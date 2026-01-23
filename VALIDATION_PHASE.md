# Validation Phase - Rules and Enforcement

## Overview

The VALIDATION phase is the fourth phase in The Lathe's phase-locked development workflow. It transitions from **code writing** to **code verification** — with strict requirements to prevent new work from entering while ensuring complete testing coverage.

---

## Phase Purpose

**Validation phase is for:**
- Verifying implementation meets design requirements
- Creating test plans and checklists
- Documenting rollback procedures
- Specifying success criteria
- Testing functionality and performance

**Validation phase is NOT for:**
- Writing new code or refactoring
- Proposing features or enhancements
- Suggesting improvements
- Adding functionality
- "Fixing" problems with new code

---

## Enforcement

### Validation Rules

The validation phase applies these validation rules:

| Rule | What It Does | Severity |
|------|--------------|----------|
| `forbid_new_code` | Blocks code blocks and snippets | FAIL |
| `forbid_new_implementation` | Prevents new implementation proposals | FAIL |
| `require_rollback_steps` | Requires rollback procedures | WARN |
| `require_checklist_format` | Requires structured test format | WARN |

---

## Forbid New Code Rule

The `ForbidNewCodeRule` prevents code blocks in validation output:

### ❌ Bad: New Code in Validation

```
VALIDATION RESULTS:

The implementation needs error handling:

export async function login(email, password) {
  try {
    const user = await db.find(email);
    return verify(password, user.hash);
  } catch (err) {
    return null;
  }
}

This should fix the issue.
```

**Why it fails:**
- Contains code block (```export async function...```)
- Adds new error handling (outside validation scope)
- Proposes implementation during validation

### ✅ Good: Validation Without Code

```
VALIDATION TEST RESULTS:

Test Case: Error Handling
- [ ] Call login with invalid email
- [ ] Verify error is thrown
- [ ] Check error message is descriptive
- [ ] Confirm app handles error gracefully

Expected Result: Error thrown and caught
Actual Result: Error thrown but not caught

Status: FAILED
Root Cause: Missing try/catch in implementation

Action Required: Rollback and re-implement with error handling
```

**Why it passes:**
- No code blocks
- References existing implementation
- Tests what was built, doesn't build new things

---

## Forbid New Implementation Rule

The `ForbidNewImplementationRule` prevents implementation proposals:

### ❌ Bad: Suggesting New Implementation

```
VALIDATION:

Current authentication is working but we should add:
1. Better password hashing with bcrypt
2. JWT token rotation
3. Rate limiting on login attempts
4. Email verification for new accounts

These improvements would make the system more secure.
```

**Why it fails:**
- "we should add" language (implementation proposal)
- Lists 4 new features
- Suggests enhancements during validation
- Moves beyond verification into development

### ✅ Good: Validation of Actual Implementation

```
VALIDATION CHECKLIST: Authentication

Authentication Service Tests:
- [ ] Valid credentials return token
- [ ] Invalid credentials return error
- [ ] Token expires after 24 hours
- [ ] Expired token is rejected

Database Tests:
- [ ] User passwords are hashed
- [ ] Hash verification works correctly
- [ ] Failed login doesn't reveal user existence

Security Tests:
- [ ] No passwords in logs
- [ ] JWT_SECRET is not exposed
- [ ] Tokens contain user ID only

Success Criteria:
- All 8 tests pass
- No security warnings
- Response time < 500ms

Rollback Procedure:
If tests fail, revert to commit XYZ123 using:
git revert XYZ123 && npm test
```

**Why it passes:**
- Only tests what was implemented
- No suggestions for new features
- No "we should add" language
- Focused on verification

---

## Require Rollback Steps Rule

The `RequireRollbackStepsRule` ensures deployment safety:

### ❌ Insufficient: Missing Rollback

```
DEPLOYMENT VERIFICATION:

Test Results: All pass
Performance: Good
Status: Ready to deploy

Deploy to production now.
```

**Why it needs improvement:**
- No rollback procedure documented
- No recovery steps if issues found
- No "undo" instructions
- Not safe for production

### ✅ Good: Complete Rollback Procedure

```
DEPLOYMENT CHECKLIST:

Pre-Deployment Verification:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Performance benchmarks acceptable
- [ ] Security scan complete
- [ ] Database backup created

Deployment Steps:
- [ ] Deploy to staging environment
- [ ] Run smoke tests on staging
- [ ] Get approval to deploy production
- [ ] Deploy to production (1 instance at a time)
- [ ] Monitor logs for errors (5 min)
- [ ] Monitor metrics for performance (5 min)

Success Criteria:
- Deployment completes without errors
- No increase in error rate
- Response time within baseline
- All services healthy

ROLLBACK PROCEDURE (if anything fails):
1. Stop traffic to production
2. Run: git revert HEAD && npm run build
3. Redeploy previous version
4. Wait for service to stabilize (2 min)
5. Verify health checks pass
6. Restore traffic gradually
7. Alert team to issue
8. Investigate root cause offline

Post-Deployment Monitoring (24 hours):
- [ ] Error rate stable or lower
- [ ] Response time stable or faster
- [ ] No customer complaints
- [ ] Database size as expected
- [ ] Cache hit rate normal
```

**Why it passes:**
- Complete deployment verification
- Clear rollback steps documented
- Recovery procedure explicit
- Safe for production deployment

---

## Require Checklist Format Rule

The `RequireChecklistFormatRule` enforces structured testing:

### ❌ Bad: Unstructured Validation

```
We tested the login system. It works pretty well.
Some things we checked:
- Valid login works
- Invalid password fails
- The response time is okay

We think it's ready to ship.
```

**Why it needs improvement:**
- Prose format instead of checklist
- No clear test cases
- No pass/fail criteria
- Not verifiable or reproducible

### ✅ Good: Structured Checklist

```
VALIDATION TEST PLAN:

Feature: User Authentication
Goal: Verify login implementation works correctly
Test Environment: Staging
Test Date: 2024-01-23

TEST CHECKLIST:

Authentication Tests:
- [ ] User can login with valid credentials
  Expected: Token returned, status 200
  Actual: [PASS]
- [ ] User cannot login with invalid password
  Expected: Error returned, status 401
  Actual: [PASS]
- [ ] User cannot login with non-existent email
  Expected: Error returned, status 401
  Actual: [PASS]

Session Tests:
- [ ] Token expires after 24 hours
  Expected: Expired token rejected
  Actual: [PASS]
- [ ] Token contains correct user ID
  Expected: JWT payload has user_id
  Actual: [PASS]

Database Tests:
- [ ] Password is stored as bcrypt hash
  Expected: Hash matches bcrypt format
  Actual: [PASS]
- [ ] User can login after password change
  Expected: New password works, old fails
  Actual: [PASS]

Performance Tests:
- [ ] Login completes within 500ms
  Expected: Response time < 500ms
  Actual: 287ms [PASS]
- [ ] Can handle 100 concurrent logins
  Expected: All succeed, no errors
  Actual: All 100 succeeded [PASS]

Security Tests:
- [ ] Passwords never appear in logs
  Expected: No password in application logs
  Actual: [PASS]
- [ ] JWT_SECRET not exposed
  Expected: No secret in error messages
  Actual: [PASS]

SUMMARY:
Total Tests: 10
Passed: 10
Failed: 0
Pass Rate: 100%

SUCCESS CRITERIA: ✅ MET
- All core functionality works
- Performance is acceptable
- No security issues found
- Ready for production deployment

LOGS TO INSPECT:
- Application logs for any errors
- Database logs for connection issues
- Performance metrics for response times
- Security audit logs for access patterns

Next Steps: Deploy to production
```

**Why it passes:**
- Clear test structure
- Pass/fail criteria explicit
- Expected vs actual documented
- Summary shows overall status
- Success criteria defined
- Easy to reproduce and verify

---

## System Prompt Enforcement

When in validation phase, the system prompt includes:

```
VALIDATION PHASE REQUIREMENTS:
- NO NEW CODE - Absolutely no code blocks or code snippets
- NO NEW IMPLEMENTATION - No refactors, features, or enhancements proposed
- MUST include rollback steps - Document recovery procedures
- MUST use checklist format - Structured, verifiable testing format
- FOCUS ON VERIFICATION - Only test what was implemented, don't build new

ALLOWED IN VALIDATION:
- Verification checklists with test steps
- Test plans and test cases
- Expected vs actual results
- Logs to inspect and error messages
- Rollback procedures and recovery steps
- Success criteria and acceptance tests
- Performance baselines and metrics

FORBIDDEN IN VALIDATION:
- Any code blocks or code fragments
- Suggestions for refactoring or improvement
- Feature enhancement proposals
- "We should add" or "we need to add" language
- New implementation ideas
- Optimization suggestions

REQUIRED STRUCTURE:
1. Test Plan (what will be tested)
2. Verification Checklist (step-by-step tests)
   - [ ] Test Case 1
   - [ ] Test Case 2
   - Expected Result: ...
   - Actual Result: ...
3. Success Criteria (define pass/fail)
4. Rollback Procedure (if tests fail)
5. Logs to Inspect (monitoring and debugging)
```

---

## Good Validation Output Example

```
VALIDATION: Authentication Service Implementation

FEATURE: User Authentication with JWT Tokens

TEST PLAN:
This validation tests the complete authentication flow including:
1. User registration and password hashing
2. User login with credential verification
3. JWT token generation and validation
4. Token expiration and refresh
5. Concurrent user handling
6. Error scenarios and edge cases

VERIFICATION CHECKLIST:

1. Registration Tests:
   - [ ] User can register with email and password
     Expected: New user created, password hashed
     Actual: [PASS] User created with bcrypt hash

   - [ ] Registration prevents duplicate emails
     Expected: Error returned for existing email
     Actual: [PASS] Unique constraint enforced

2. Login Tests:
   - [ ] User can login with correct credentials
     Expected: JWT token returned, 200 OK
     Actual: [PASS] Token: eyJhbGciOi... (valid)

   - [ ] Login fails with incorrect password
     Expected: 401 Unauthorized
     Actual: [PASS] Correct error returned

   - [ ] Login fails with non-existent email
     Expected: 401 Unauthorized, no user enumeration
     Actual: [PASS] Same error message as wrong password

3. Token Validation Tests:
   - [ ] Valid token is accepted
     Expected: Request succeeds with valid token
     Actual: [PASS] Request processed correctly

   - [ ] Expired token is rejected
     Expected: 401 Unauthorized, error message "Token expired"
     Actual: [PASS] Correct error message

   - [ ] Modified token is rejected
     Expected: 401 Unauthorized, error message "Invalid token"
     Actual: [PASS] Tampering detected

4. Performance Tests:
   - [ ] Login completes within 500ms
     Expected: Response time < 500ms
     Actual: [PASS] Average: 147ms, Max: 289ms

   - [ ] Can handle 50 concurrent logins
     Expected: All succeed without timeout
     Actual: [PASS] All 50 completed successfully

5. Security Tests:
   - [ ] Passwords stored as bcrypt hashes
     Expected: No plaintext passwords in database
     Actual: [PASS] All passwords use bcrypt, rounds=10

   - [ ] JWT_SECRET is not exposed
     Expected: Secret not in logs or errors
     Actual: [PASS] No secret leaks detected

   - [ ] No sensitive data in JWT token
     Expected: Only user_id in token payload
     Actual: [PASS] Token contains only user_id

   - [ ] Rate limiting prevents brute force
     Expected: Multiple failed logins blocked
     Actual: [PASS] 5+ attempts blocked per IP

TEST EXECUTION SUMMARY:
Environment: Staging
Test Date: 2024-01-23 14:30 UTC
Tester: qa-team
Total Test Cases: 11
Passed: 11
Failed: 0
Skipped: 0
Success Rate: 100%

Test Duration:
- Functional tests: 2.3 minutes
- Performance tests: 4.1 minutes
- Security tests: 1.8 minutes
- Total: 8.2 minutes

LOGS TO INSPECT:
- Application logs: /var/log/auth-app/app.log
- Database logs: /var/log/postgres/auth.log
- Performance metrics: Datadog dashboard (link)
- Security audit: /var/log/security/audit.log

Key Metrics:
- Database query time: avg 45ms
- Password hash time: avg 120ms (bcrypt)
- Token validation time: avg 2ms
- API response time: avg 165ms

SUCCESS CRITERIA:
✅ All core functionality tests pass
✅ Performance meets SLA (< 500ms)
✅ Security tests pass
✅ No errors in logs
✅ Can handle expected load (50 concurrent)
✅ Ready for production deployment

ROLLBACK PROCEDURE (if issues found):

1. Identify Issue:
   - Check application logs for errors
   - Verify error rate from monitoring
   - Confirm it's related to this deployment

2. Stop New Deployments:
   - Cancel any in-progress deployments
   - Prevent additional instances from starting

3. Revert Code:
   - SSH into production: ssh prod-api-01
   - Check current version: git describe --tags
   - Get previous stable version: git log --oneline | head -5
   - Revert: git revert HEAD && git push origin main
   - Wait for CI/CD pipeline (typically 3-5 min)

4. Redeploy Previous Version:
   - Trigger deployment in CI/CD: Deploy prod-api v1.2.3
   - Monitor rollout progress
   - Verify all instances deployed

5. Verify Stability:
   - Check error rate returns to baseline
   - Verify no more alerts firing
   - Confirm users can login
   - Check response times are normal

6. Monitor Post-Rollback:
   - Watch logs for next 30 minutes
   - Monitor error rate
   - Monitor performance metrics
   - Document issue for post-mortem

7. Notify Team:
   - Post in #incident channel
   - Schedule post-mortem within 24 hours
   - Investigate root cause offline

ARTIFACTS:
- Test results: /artifacts/validation/auth-test-results.json
- Performance report: /artifacts/validation/auth-performance.pdf
- Security scan: /artifacts/validation/auth-security-scan.html
- Deployment checklist: /artifacts/validation/auth-deployment-checklist.md

APPROVAL: ✅ READY FOR PRODUCTION

Validated by: qa-team
Approval: DevOps Lead (john-smith@company.com)
Deployment Window: Available 24/7 (no customer impact expected)
```

---

## Phase Progression

| Aspect | Implementation | Validation |
|--------|-----------------|-----------|
| **Purpose** | Write code | Test code |
| **Code** | Required output | Forbidden output |
| **Output Type** | Complete files | Test plans |
| **Structure** | Full replacement | Checklist format |
| **New Work** | Required | Forbidden |
| **Assumptions** | Documented | Not needed |
| **Next Phase** | → Validation | → Hardening |

---

## Common Mistakes

### Mistake 1: New Code in Validation

```
❌ WRONG:
We should also add better error handling:

try {
  const user = login(email, password);
} catch (err) {
  console.log(err);
}
```

```
✅ CORRECT:
Test Case: Error Handling
- [ ] Login with invalid email
  Expected: Error thrown
  Actual: [To be tested]
```

### Mistake 2: Missing Rollback

```
❌ WRONG:
All tests pass. Deploy now.
```

```
✅ CORRECT:
All tests pass.

Rollback Procedure:
1. If tests fail, revert to commit ABC123
2. Run: git revert ABC123 && npm run build
3. Deploy previous version
4. Verify services are healthy
```

### Mistake 3: Unstructured Testing

```
❌ WRONG:
We tested the login. It works.
Some tests passed, most failed.
Seems okay to ship.
```

```
✅ CORRECT:
Test Case: Valid Login
- [ ] User can login with correct credentials
  Expected: 200 OK, token returned
  Actual: [PASS] Token generated successfully

Test Results:
- Total: 10
- Passed: 10
- Failed: 0
- Success Rate: 100%
```

### Mistake 4: No Success Criteria

```
❌ WRONG:
We ran the tests. Here are the results.
Some things work, others need work.
```

```
✅ CORRECT:
Success Criteria:
- [ ] All unit tests pass (10/10)
- [ ] Performance < 500ms (avg 145ms)
- [ ] No security warnings
- [ ] Load test handles 50 concurrent (yes)
- [ ] Zero errors in logs

Overall: ✅ PASS - Ready for deployment
```

---

## Testing Strategies

### Unit Tests
- Test individual functions
- Test error cases
- Test edge cases
- Verify return values

### Integration Tests
- Test component interactions
- Test API endpoints
- Test database operations
- Test full workflows

### Performance Tests
- Measure response times
- Test under load
- Verify SLA compliance
- Identify bottlenecks

### Security Tests
- No secrets in logs
- Proper authentication
- Proper authorization
- Input validation

### Smoke Tests
- Verify basic functionality
- Quick deployment verification
- Sanity checks after deployment

---

## Success Criteria Definition

Good success criteria are:
- **Specific** - Clear what must pass
- **Measurable** - Can verify pass/fail
- **Achievable** - Realistic expectations
- **Relevant** - Related to requirements
- **Timely** - Can be tested within deployment window

### Example: Poor Success Criteria
```
The system should work well.
Performance should be good.
Security should be strong.
```

### Example: Good Success Criteria
```
- Login response time < 500ms (avg of 100 requests)
- Zero authentication failures with valid credentials
- All SQL queries use parameterized statements
- Passwords stored as bcrypt hashes, rounds >= 10
- No secrets in application logs
- System handles 50 concurrent users
```

---

## Output Structure Checklist

All validation outputs should include:

```
✅ Test Plan
   - What will be tested
   - Why it matters
   - How it will be tested

✅ Test Cases
   - Clear case descriptions
   - Expected results
   - Actual results
   - Pass/Fail status

✅ Success Criteria
   - Explicit pass/fail thresholds
   - Overall success determination
   - Ready/not-ready for next phase

✅ Rollback Procedure
   - Steps to revert if issues found
   - Recovery time estimate
   - Escalation contacts

✅ Logs and Artifacts
   - What logs to inspect
   - Where metrics are available
   - How to debug if issues
```

---

## Integration with OpenWebUI

When using the Lathe tool in OpenWebUI:

1. **User requests validation:** "Create validation test plan for auth service"

2. **lathe_plan called:**
   - Returns system prompt with validation phase rules
   - Emphasizes NO NEW CODE, NO NEW IMPLEMENTATION
   - Requires checklist format and rollback procedure

3. **LLM generates validation plan:**
   - Test cases with expected/actual results
   - Structured checklist format
   - Complete rollback procedure
   - Success criteria defined

4. **lathe_validate called:**
   - Validates no code blocks → MUST PASS
   - Validates no implementation proposals → MUST PASS
   - Validates rollback steps included → WARNS if missing
   - Validates checklist format used → WARNS if missing

5. **OpenWebUI displays result:**
   - Shows validation status
   - Lists any warnings about rollback or format
   - Can proceed to next phase if all pass

---

## Safety Constraints

Validation phase is **safe by constraint:**

❌ **Does NOT:**
- Execute code
- Auto-fix errors
- Write to disk
- Modify system state
- Run commands

✅ **Only:**
- Validates output format
- Returns analysis
- Provides test planning

---

## Phase Summary

| Element | Details |
|---------|---------|
| **Phase Name** | VALIDATION |
| **Purpose** | Verify implementation works |
| **Rules** | 4 rules (2 FAIL, 2 WARN) |
| **Forbidden** | New code, new implementation |
| **Required** | Checklists, rollback, criteria |
| **Output** | Test plans, test cases |
| **Next** | → HARDENING |

---

## Testing Commands

### Run Validation Test Suite
```bash
python3 << 'EOF'
from lathe_tool import lathe_validate

# Test 1: Code blocks fail
bad1 = """
VALIDATION:

export function login() { }

This should be added.
"""
result = lathe_validate("validation", bad1)
print(f"Code blocks: {result['status']} (expect 'fail')")

# Test 2: Implementation proposal fails
bad2 = """
VALIDATION:

We should add better error handling and logging to the system.
Let's also implement rate limiting.
"""
result = lathe_validate("validation", bad2)
print(f"Implementation proposal: {result['status']} (expect 'fail')")

# Test 3: Good validation passes
good = """
VALIDATION CHECKLIST:

Test Cases:
- [ ] User can login with valid credentials
  Expected: Token returned
  Actual: [PASS]

Success Criteria:
- All tests pass: YES
- Performance OK: YES
- Ready to deploy: YES

Rollback Procedure:
If deployment fails, run: git revert HEAD && deploy
"""
result = lathe_validate("validation", good)
print(f"Good validation: {result['status']} (expect 'pass' or 'warn')")
EOF
```

---

**Status:** ✅ Phase 4 Implemented

**Validation Rules:** 4 total (2 FAIL critical, 2 WARN guidance)

**Safety:** No execution, no persistence, no state changes

**Purpose:** Force verification thinking, prevent new work from entering

---

## Next Phase

After validation is complete:
- **→ HARDENING phase** - Security hardening and final checks
- Validation becomes input to hardening
- Cycle back if critical issues found
