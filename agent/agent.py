import json
import os
import re
from datetime import datetime, time as dt_time

import anthropic
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "hybrid_ids"),
}


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")
CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "500"))

_claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None



ATTACK_CONTEXT = {
    "DoS Hulk": (
        "A high-volume HTTP flood consistent with a Denial-of-Service attack, overwhelming a "
        "web service with requests.", "rarely"
    ),
    "DDoS": (
        "A distributed denial-of-service flood, typically driven by many coordinated sources "
        "to exhaust a service's capacity.", "rarely"
    ),
    "PortScan": (
        "Systematic scanning of ports/services, often reconnaissance ahead of an attack -- but "
        "this exact pattern is also commonly produced by legitimate internal vulnerability "
        "scanners or IT audit tools.", "often"
    ),
    "Bot": (
        "Traffic consistent with botnet command-and-control communication, which can indicate a "
        "compromised host -- but can also resemble a scheduled automated script or monitoring agent.",
        "sometimes"
    ),
    "SSH-Patator": (
        "Repeated SSH login attempts consistent with a brute-force credential attack against a server.",
        "sometimes"
    ),
    "FTP-Patator": (
        "Repeated FTP login attempts consistent with a brute-force credential attack.",
        "sometimes"
    ),
    "Web Attack – Brute Force": (
        "Repeated login attempts against a web application, consistent with credential brute-forcing.",
        "sometimes"
    ),
    "Web Attack – XSS": (
        "Traffic consistent with a cross-site scripting injection attempt against a web application.",
        "rarely"
    ),
    "Web Attack – Sql Injection": (
        "Traffic consistent with an SQL injection attempt targeting a web application's database layer.",
        "rarely"
    ),
    "Infiltration": (
        "Traffic consistent with an attempted internal compromise -- for example, an employee "
        "downloading a malicious payload, opening a weaponised attachment, or a foothold being "
        "established on their machine, potentially followed by attempted data exfiltration.",
        "rarely"
    ),
    "Heartbleed": (
        "Traffic consistent with exploitation of the Heartbleed OpenSSL vulnerability to extract "
        "sensitive memory contents such as credentials or private keys from a server.",
        "rarely"
    ),
}
DEFAULT_ATTACK_CONTEXT = ("Traffic flagged by the anomaly detection model as anomalous.", "sometimes")


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def find_employee_by_ip(cursor, src_ip: str):
    cursor.execute("SELECT * FROM employees WHERE ip_address = %s", (src_ip,))
    return cursor.fetchone()


def find_relevant_tickets(cursor, employee_id: int, alert_time: datetime):
    cursor.execute(
        """
        SELECT * FROM tickets
        WHERE employee_id = %s
          AND (
                status IN ('open', 'in_progress')
                OR (status IN ('resolved', 'closed') AND resolved_at >= %s)
              )
        ORDER BY created_at DESC
        """,
        (employee_id, alert_time - _timedelta(hours=24)),
    )
    return cursor.fetchall()


def find_active_leave(cursor, employee_id: int, alert_date):
    cursor.execute(
        """
        SELECT * FROM leave_records
        WHERE employee_id = %s
          AND approved = TRUE
          AND %s BETWEEN start_date AND end_date
        """,
        (employee_id, alert_date),
    )
    return cursor.fetchall()


def _timedelta(**kwargs):
    from datetime import timedelta
    return timedelta(**kwargs)


def _seconds_since_midnight(value) -> int:
    if isinstance(value, dt_time):
        return value.hour * 3600 + value.minute * 60 + value.second
    if hasattr(value, "total_seconds"):  
        return int(value.total_seconds()) % 86400
    raise TypeError(f"Unsupported time value type: {type(value)}")


def is_within_work_hours(alert_time: datetime, work_start, work_end) -> bool:
    t = _seconds_since_midnight(alert_time.time())
    start = _seconds_since_midnight(work_start)
    end = _seconds_since_midnight(work_end)

    if start <= end:
        
        return start <= t < end
    else:
        
        return t >= start or t < end



def build_prompt(alert: dict, employee, tickets, leave_records, in_work_hours: bool) -> str:
    if employee is None:
        employee_section = "No employee record is associated with this source IP. This IP is unrecognised."
    else:
        employee_section = (
            f"Employee: {employee['name']}\n"
            f"Department: {employee['department']}\n"
            f"Role: {employee['role']}\n"
            f"Clearance level: {employee['clearance_level']}\n"
            f"Normal working hours: {employee['work_start']} - {employee['work_end']}\n"
            f"Alert occurred within normal working hours: {'Yes' if in_work_hours else 'No'}"
        )

    if tickets:
        ticket_lines = "\n".join(
            f"  - [{t['type']}] status={t['status']}: {t['description']}"
            for t in tickets
        )
        ticket_section = f"Relevant tickets:\n{ticket_lines}"
    else:
        ticket_section = "Relevant tickets: none found."

    if leave_records:
        leave_section = "Employee is on APPROVED leave covering this date."
    else:
        leave_section = "Employee is not on approved leave for this date."

    attack_description, explainability = ATTACK_CONTEXT.get(alert["label"], DEFAULT_ATTACK_CONTEXT)

    prompt = f"""You are a SOC (Security Operations Centre) triage analyst assistant.
An anomaly detection model has flagged the following network alert as a potential attack.
Your job is to decide whether this is a TRUE POSITIVE (a genuine security incident requiring
investigation) or a FALSE POSITIVE (explainable by legitimate organisational context).
 
=== ALERT ===
Source IP: {alert['src_ip']}
Destination Port: {alert['dst_port']}
Protocol: {alert['protocol']}
Detected label: {alert['label']}
Model confidence: {alert['confidence']}
Timestamp: {alert['timestamp']}
 
=== WHAT THIS ATTACK TYPE MEANS ===
{attack_description}
Traffic of this shape is {explainability} explainable by legitimate employee/IT activity, even
when a matching ticket or work-hours context exists -- weigh that in your verdict. A severe or
purely destructive pattern (e.g. a volumetric flood, a credential-extraction exploit) should stay
a true positive even if the source happens to resolve to an employee, unless the organisational
context specifically and directly accounts for that exact kind of activity (e.g. an approved
penetration-testing or vulnerability-scanning ticket).
 
=== ORGANISATIONAL CONTEXT ===
{employee_section}
 
{ticket_section}
 
{leave_section}
 
=== INSTRUCTIONS ===
Weigh the alert against both what this attack type actually represents AND the organisational
context above. Your reasoning must describe the specific nature of the activity (e.g. "this
pattern is consistent with an attempted malware download" or "this resembles a routine internal
port scan"), not only cite IP-matching or ticket lookups mechanically. For example, PortScan or
Bot-style traffic from an employee with a matching IT-maintenance ticket and who is within working
hours is plausibly a false positive; an Infiltration or Heartbleed-style alert, or any alert from
an unrecognised IP with no ticket, no leave, and outside working hours, is plausibly a true positive
requiring investigation.
 
The "WHAT THIS ATTACK TYPE MEANS" text above is background knowledge for YOU only -- do not quote
or closely paraphrase it back in your reasoning. Instead, write your reasoning by referencing the
SPECIFIC details of this case: the employee's actual name and role if one exists, the exact wording
of any matching ticket, the exact time of day versus their actual shift, and so on. Two alerts with
the same detected label should still read as distinct explanations, because the organisational
details behind them are different.
 
HARD RULE, apply this before deciding: a false_positive verdict requires a SPECIFIC ticket or
approved leave record that directly and specifically corroborates THIS activity (for example, a
ticket that explicitly authorises a vulnerability scan, penetration test, load test, or a
maintenance window covering this exact port or service). Role plausibility, department, seniority,
clearance level, or reasoning such as "this could plausibly be routine IT/compliance/audit work"
is NEVER sufficient on its own, no matter how well it fits the employee's job title. If
"Relevant tickets: none found" appears above, or no ticket on file specifically covers this exact
activity, you MUST return true_positive -- even if the employee has high clearance, even if the
alert occurred within their normal working hours, and even if the traffic lacks an overtly
destructive payload. Absence of evidence is not evidence of absence: unticketed scanning or
flooding from a real employee's account is exactly what a compromised or misused legitimate
account looks like, and it must be escalated, not explained away.
 
GROUNDING RULE: every specific detail in your reasoning (ticket wording, employee name, role,
department, working hours) must come only from the ORGANISATIONAL CONTEXT section above. If you
mention what a ticket says, you must use only words and facts that literally appear in that
ticket's description text -- never infer, guess, or invent a purpose, system name, or project name
for a ticket that is not explicitly written there. If no ticket, employee, or leave record is shown
above, say so plainly rather than describing plausible-sounding activity that was never provided to
you.
 
Respond with ONLY a JSON object, no other text, in exactly this format:
{{"verdict": "true_positive" or "false_positive", "reasoning": "a concise natural-language explanation"}}
Keep the reasoning on a single line with no literal line breaks inside the string.
"""
    return prompt


def call_claude(prompt: str) -> str:
    if _claude_client is None:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to agent/.env "
            "(get a key from console.anthropic.com -- separate from a Pro/Max subscription)."
        )
    response = _claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=CLAUDE_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def parse_llm_response(raw_response: str) -> dict:
  
    match = re.search(r"\{.*\}", raw_response, re.DOTALL)
    if not match:
        return {
            "verdict": "true_positive",  
            "reasoning": f"Agent response could not be parsed as JSON. Raw response: {raw_response[:300]}",
        }

    candidate = match.group(0)

    
    parsed = _try_json_load(candidate)

    
    if parsed is None:
        sanitized = re.sub(r"[\r\n\t]+", " ", candidate)
        parsed = _try_json_load(sanitized)

    
    if parsed is None:
        verdict_match = re.search(r'"verdict"\s*:\s*"(true_positive|false_positive)"', candidate)
        reasoning_match = re.search(r'"reasoning"\s*:\s*"(.*?)"\s*\}?\s*$', candidate, re.DOTALL)
        if verdict_match:
            parsed = {
                "verdict": verdict_match.group(1),
                "reasoning": (reasoning_match.group(1).strip() if reasoning_match
                              else "Reasoning field could not be cleanly extracted from a malformed response."),
            }

    if parsed is None:
        return {
            "verdict": "true_positive",
            "reasoning": f"Agent response was not valid JSON. Raw response: {raw_response[:300]}",
        }

    verdict = parsed.get("verdict", "true_positive")
    if verdict not in ("true_positive", "false_positive"):
        verdict = "true_positive"

    reasoning = parsed.get("reasoning", "No reasoning provided.")
    return {"verdict": verdict, "reasoning": reasoning}


def _try_json_load(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None






def triage_alert(alert: dict) -> dict:
 
    alert_time = alert["timestamp"]
    if isinstance(alert_time, str):
        alert_time = datetime.fromisoformat(alert_time)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    employee = find_employee_by_ip(cursor, alert["src_ip"])

    tickets = []
    leave_records = []
    in_work_hours = False

    if employee:
        tickets = find_relevant_tickets(cursor, employee["id"], alert_time)
        leave_records = find_active_leave(cursor, employee["id"], alert_time.date())
        in_work_hours = is_within_work_hours(
            alert_time, employee["work_start"], employee["work_end"]
        )

    cursor.close()
    conn.close()

    prompt = build_prompt(
        {**alert, "timestamp": alert_time}, employee, tickets, leave_records, in_work_hours
    )
    raw_response = call_claude(prompt)
    result = parse_llm_response(raw_response)
    return result


if __name__ == "__main__":
    
    test_alert = {
        "src_ip": "10.0.1.5",
        "dst_port": 3389,
        "protocol": "TCP",
        "label": "PortScan",
        "confidence": 0.93,
        "timestamp": datetime.now().isoformat(),
    }
    print(json.dumps(triage_alert(test_alert), indent=2))