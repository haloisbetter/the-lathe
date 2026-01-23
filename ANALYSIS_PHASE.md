# Analysis Phase - Rules and Enforcement

## Overview

The ANALYSIS phase is the first phase in The Lathe's phase-locked development workflow. It is strictly limited to **discovery, observation, and risk identification** — **NO CODE, NO DESIGN, NO IMPLEMENTATION**.

---

## Phase Purpose

**Analysis phase is for:**
- Understanding requirements
- Identifying risks and unknowns
- Documenting assumptions
- Discovering edge cases
- Asking clarifying questions
- Summarizing findings

**Analysis phase is NOT for:**
- Writing code
- Creating architecture diagrams
- Designing solutions
- Implementing features
- Providing file paths
- Executing commands

---

## Enforcement

### Validation Rule: `NoCodeOutputRule`

The analysis phase uses the `NoCodeOutputRule` validation rule that **FAILS** if any of the following are detected:

#### 1. Code Blocks

❌ **Forbidden:**
```
def authenticate(user):
    return True
```

❌ **Forbidden:**
```javascript
function login() { ... }
```

✅ **Allowed:**
Discussing that "the authenticate function needs error handling" without showing code.

#### 2. Code Keywords

❌ **Forbidden:**
- `def authenticate(...)`
- `class UserManager`
- `import requests`
- `function login()`
- `const apiKey =`
- `let user =`
- `var data =`
- `return result`
- `if (condition)`
- `for (item in list)`

✅ **Allowed:**
Discussing "the function" or "the class" in prose without showing implementations.

#### 3. File Paths

❌ **Forbidden:**
- `/src/auth/login.py`
- `/app/models/user.js`
- `./components/Header.tsx`
- `file://path/to/config`

✅ **Allowed:**
Generic references like "the authentication module" or "user model file" without specific paths.

#### 4. Shell Commands

❌ **Forbidden:**
```bash
$ npm install express
$ pip install requests
$ docker run myapp
$ git clone repo
```

✅ **Allowed:**
Discussing "the system needs Express installed" without showing the command.

#### 5. Inline Code Snippets

❌ **Forbidden (multiple instances):**
The system uses `apiKey` and `userId` to authenticate requests.

✅ **Allowed (minimal technical terms):**
The system uses an API key and user identifier for authentication.

---

## What IS Allowed

### ✅ Findings and Observations

```
FINDINGS:
- The authentication system currently lacks rate limiting
- Users can attempt unlimited login retries
- Password reset flow is not documented
```

### ✅ Risk Identification

```
RISKS:
- Brute force attacks possible due to no rate limiting
- User enumeration via password reset timing
- Session tokens may not expire properly
```

### ✅ Requirements Discovery

```
REQUIREMENTS:
- System must support OAuth2 authentication
- Password must meet HIPAA complexity requirements
- Session timeout must be configurable
```

### ✅ Assumptions and Unknowns

```
ASSUMPTIONS:
- Users have valid email addresses
- System can send email notifications
- Database supports transaction isolation

UNKNOWNS:
- What is the expected concurrent user load?
- Are there specific compliance requirements?
- Should we support multi-factor authentication?
```

### ✅ Questions

```
QUESTIONS TO RESOLVE:
1. What is the maximum acceptable login time?
2. Should failed login attempts be logged?
3. Are there specific password complexity rules?
```

### ✅ Problem Statement

```
PROBLEM:
Users report that login takes too long during peak hours.
The system shows high database query times during authentication.
No caching layer exists for frequently accessed user data.
```

---

## System Prompt Enforcement

When in analysis phase, the system prompt includes:

```
CRITICAL ANALYSIS PHASE RULES:
- NO CODE OUTPUT - You must not write any code blocks, snippets, or implementations
- NO DESIGN ARTIFACTS - Do not create architecture diagrams or design documents
- NO FILE PATHS - Do not reference specific file locations
- NO COMMANDS - Do not provide shell commands or executable instructions

ALLOWED IN ANALYSIS:
- Findings and observations
- Risk identification
- Problem statement
- Requirements discovery
- Assumptions and unknowns
- Questions that need answers

OUTPUT MUST BE PROSE ONLY.
```

---

## Validation Rules Applied

The analysis phase applies these validation rules by default:

1. **`no_code_output`** (FAIL) - No code blocks, keywords, paths, or commands
2. **`explicit_assumptions`** (WARN) - Must document assumptions clearly
3. **`required_section`** (WARN) - Must include: Findings, Risks, Next Steps

---

## Phase Transition

After analysis is complete and validated, you can proceed to:

**→ DESIGN phase** - Create architecture, plan interfaces, document trade-offs

Analysis cannot skip directly to implementation.

---

## Examples

### ❌ Bad Analysis Output (FAILS Validation)

```
ANALYSIS RESULTS:

The authentication system needs improvement. Here's the fix:

```python
def authenticate(username, password):
    user = db.query("SELECT * FROM users WHERE username = ?", username)
    if bcrypt.check(password, user.password_hash):
        return create_session(user)
    return None
```

To deploy: `docker run -p 8080:8080 auth-service`
```

**Why it fails:**
- Contains code blocks (Python)
- Shows implementation
- Includes shell command

---

### ✅ Good Analysis Output (PASSES Validation)

```
ANALYSIS RESULTS:

FINDINGS:
- The current authentication system lacks secure password hashing
- No session management or timeout mechanism exists
- Database queries are not parameterized, creating SQL injection risk

RISKS:
- High - Password storage is vulnerable to rainbow table attacks
- High - Sessions never expire, allowing indefinite access
- Critical - SQL injection possible in username field

ASSUMPTIONS:
- Users access the system via HTTP/HTTPS protocol
- A database layer exists for user storage
- System has the capability to generate and store secure tokens

UNKNOWNS:
- What password complexity requirements are needed?
- Should sessions persist across browser restarts?
- Are there regulatory compliance requirements (HIPAA, GDPR)?

NEXT STEPS:
1. Clarify password policy requirements
2. Determine session timeout policy
3. Proceed to design phase for authentication architecture
```

**Why it passes:**
- Pure prose, no code
- Documents findings and risks
- States assumptions clearly
- Identifies unknowns
- No file paths or commands

---

## Testing

Test the analysis phase enforcement:

```python
from lathe_tool import lathe_plan, lathe_validate

# Prepare analysis phase
plan = lathe_plan(
    project="myapp",
    scope="authentication",
    phase="analysis",
    goal="Analyze authentication system security"
)

# Validate output with code (should FAIL)
bad_output = """
FINDINGS: Authentication is broken.

Fix:
```python
def fix_auth():
    return True
```
"""

result = lathe_validate(phase="analysis", output=bad_output)
assert result["status"] == "fail"
assert result["can_proceed"] == False

# Validate prose-only output (should PASS)
good_output = """
FINDINGS:
- Authentication system lacks password hashing
- No rate limiting on login attempts

RISKS:
- Brute force attacks possible
- Password database vulnerable to breach

ASSUMPTIONS:
- Users have valid email addresses
- System can enforce password policies
"""

result = lathe_validate(phase="analysis", output=good_output)
assert result["status"] == "pass" or result["status"] == "warn"
assert result["can_proceed"] == True
```

---

## Integration with OpenWebUI

When using the Lathe tool in OpenWebUI:

```
User: "Analyze the authentication system and identify security risks"

OpenWebUI:
1. Calls lathe_plan(phase="analysis", ...)
2. Receives system prompt with NO CODE enforcement
3. Sends to LLM with strict instructions
4. LLM generates analysis (prose only)
5. Calls lathe_validate(phase="analysis", output=...)
6. If code detected → FAIL, ask user to regenerate
7. If prose only → PASS, proceed
```

---

## Summary

| Aspect | Analysis Phase |
|--------|---------------|
| **Purpose** | Discovery, observation, risk identification |
| **Output** | Prose, findings, risks, questions |
| **Validation** | NoCodeOutputRule (FAIL on code) |
| **Allows** | Findings, risks, assumptions, unknowns |
| **Forbids** | Code, designs, file paths, commands |
| **Next Phase** | Design |

---

## Key Principle

**Analysis is for THINKING, not BUILDING.**

The model must resist the urge to solve problems during analysis. Analysis identifies problems, risks, and requirements. Solutions come in later phases.

---

## Support

- **Implementation:** `lathe/validation/rules.py` → `NoCodeOutputRule`
- **Enforcement:** `lathe_tool.py` and `lathe/tool/wrapper.py`
- **Testing:** `tests/test_tool_wrapper.py`
- **Phase Discipline:** Phase-locked workflow prevents code in analysis

---

**Status:** ✅ Implemented and enforced
**Severity:** FAIL (analysis with code will not pass validation)
**Default:** Enabled for all analysis phase operations
