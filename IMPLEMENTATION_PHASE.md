# Implementation Phase - Rules and Enforcement

## Overview

The IMPLEMENTATION phase is the third phase in The Lathe's phase-locked development workflow. It transitions from **architectural design** to **concrete, complete code** — with strict requirements for clarity, safety, and determinism.

---

## Phase Purpose

**Implementation phase is for:**
- Writing complete, executable code
- Providing full file replacements (not snippets)
- Implementing designed architecture
- Creating migrations and configuration
- Specifying explicit deployment steps
- Making deterministic, reproducible implementations

**Implementation phase is NOT for:**
- Presenting multiple alternatives ("pick one approach")
- Suggesting partial snippets ("add this to line 42")
- Making assumptions ("assume this file exists")
- Providing vague references
- Leaving behavioral gaps

---

## Enforcement

### Validation Rules

The implementation phase applies these validation rules:

| Rule | What It Does | Severity |
|------|--------------|----------|
| `require_explicit_filename` | Requires clear file path declaration | FAIL |
| `require_full_file_replacement` | Blocks partial/incomplete content | FAIL |
| `forbid_multiple_implementations` | Prevents alternative approaches | FAIL |
| `explicit_assumptions` | Documents all prerequisites | WARN |

---

## Explicit Filename Rule

The `RequireExplicitFilenameRule` requires clear file path declaration:

❌ **Forbidden:** Vague filename

```
Here's the authentication code:

function authenticate(user, password) {
  return bcrypt.verify(password, user.hash);
}
```

**Why it fails:**
- No filename declared
- User doesn't know where to put this
- Ambiguous file location

✅ **Required:** Explicit filename

```
File: src/auth/authenticate.ts

Complete file replacement:

export function authenticate(user: User, password: string): boolean {
  return bcrypt.verify(password, user.hash);
}
```

**Why it passes:**
- Clear file path: `src/auth/authenticate.ts`
- Location is explicit
- User knows exactly where to put code

---

## Full File Replacement Rule

The `RequireFullFileReplacementRule` requires complete file content:

### ❌ Bad: Partial Snippets

```
Update the database connection file:

Add this function:

function query(sql) {
  return pool.query(sql);
}

// ... rest of file unchanged
```

**Why it fails:**
- Uses "... rest of file" pattern
- Incomplete content
- Assumes existing code
- Cannot reproduce independently

### ✅ Good: Complete File

```
File: src/db/connection.ts

Full file replacement:

import { Pool } from 'pg';

const pool = new Pool({
  host: process.env.DB_HOST,
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
});

export async function query(sql: string, values: any[] = []) {
  const result = await pool.query(sql, values);
  return result.rows;
}

export async function queryOne(sql: string, values: any[] = []) {
  const result = await pool.query(sql, values);
  return result.rows[0] || null;
}

export async function execute(sql: string, values: any[] = []) {
  return await pool.query(sql, values);
}

export async function transaction(fn: (client: any) => Promise<void>) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await fn(client);
    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}

export async function close() {
  await pool.end();
}
```

**Why it passes:**
- Complete file content with all imports
- All functions fully implemented
- No external dependencies assumed
- Can be dropped in directly

---

## Multiple Implementations Rule

The `ForbidMultipleImplementationsRule` prevents alternative approaches:

### ❌ Bad: Multiple Options

```
IMPLEMENTATION:

Option 1: Using Redis Cache
Create a cache service that stores data in Redis.
// Redis implementation

Option 2: Using Local Memory Cache
Create an in-memory cache using a Map.
// Memory implementation

Choose whichever approach fits your use case.
```

**Why it fails:**
- Two different implementations
- "Choose one" scenario
- User must decide
- Ambiguous final state

### ✅ Good: Single Implementation

```
File: src/services/cache.ts

Full file replacement:

Based on the design phase decision to use Redis,
here is the implementation:

import redis from 'redis';

class CacheService {
  private client: redis.RedisClient;

  constructor() {
    this.client = redis.createClient({
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379'),
    });
  }

  async get(key: string): Promise<string | null> {
    return new Promise((resolve, reject) => {
      this.client.get(key, (err, val) => {
        if (err) reject(err);
        resolve(val);
      });
    });
  }

  async set(key: string, value: string, ttl?: number): Promise<void> {
    return new Promise((resolve, reject) => {
      if (ttl) {
        this.client.setex(key, ttl, value, (err) => {
          if (err) reject(err);
          resolve();
        });
      } else {
        this.client.set(key, value, (err) => {
          if (err) reject(err);
          resolve();
        });
      }
    });
  }

  async delete(key: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.client.del(key, (err) => {
        if (err) reject(err);
        resolve();
      });
    });
  }

  close(): void {
    this.client.quit();
  }
}

export default new CacheService();
```

**Why it passes:**
- Single, clear implementation
- References design decision
- Complete, working code
- No alternatives

---

## Explicit Assumptions Rule

The `ExplicitAssumptionsRule` documents prerequisites:

### ❌ Insufficient: Vague Assumptions

```
Implementation for authentication:

Make sure you have the dependencies installed
and the database configured properly.
```

**Why it needs improvement:**
- Vague prerequisites
- User doesn't know what's needed
- No specific versions or configurations

### ✅ Good: Explicit Assumptions

```
ASSUMPTIONS:
1. Node.js 16+ is installed
2. PostgreSQL database running and accessible
3. Environment variables configured:
   - DB_HOST (default: localhost)
   - DB_PORT (default: 5432)
   - DB_NAME
   - DB_USER
   - DB_PASSWORD
4. npm dependencies installed: pg, bcrypt, jsonwebtoken

PREREQUISITES CHECKLIST:
- [ ] PostgreSQL server running
- [ ] .env file has database credentials
- [ ] npm install completed
- [ ] npm run build completed (if required)

File: src/auth/service.ts

Full file replacement:
[implementation here]
```

**Why it passes:**
- All prerequisites explicit
- Versions specified
- Environment variables named
- Checklist provided

---

## System Prompt Enforcement

When in implementation phase, the system prompt includes:

```
IMPLEMENTATION PHASE REQUIREMENTS:
- MUST have explicit filename(s) - Declare which file(s) are being modified
- MUST provide FULL file replacement - Complete file content, no snippets
- MUST be single implementation - No alternatives or "pick one" scenarios
- NO partial snippets - Avoid "... rest of file", "assume this exists", etc.
- ALL assumptions MUST be explicit - State any prerequisites clearly

ALLOWED IN IMPLEMENTATION:
- Complete file content with imports and full structure
- Code with proper error handling
- Database migrations with full SQL
- Configuration files (complete)
- Comments explaining non-obvious logic
- File paths with clear directory structure

FORBIDDEN IN IMPLEMENTATION:
- Inline code snippets ("just add this to line 42")
- "Assume this file exists" patterns
- Multiple alternative implementations
- Partial content ("... rest of")
- Vague references to existing code
- Unspecified behavior

REQUIRED STRUCTURE:
1. Filename/File Path (explicit)
2. Assumptions Section (if any prerequisites)
3. Complete File Content (entire file replacement)
4. Usage Instructions (how to deploy/test)

SAFETY CONSTRAINTS:
- No shell execution
- No auto-fix attempts
- No persistent state changes
- Output only - no validation
```

---

## Good Implementation Output Example

```
IMPLEMENTATION: User Authentication Service

FILE: src/services/auth.service.ts

ASSUMPTIONS:
1. PostgreSQL database configured
2. Environment variables set:
   - JWT_SECRET (32+ character string)
   - PASSWORD_ROUNDS (bcrypt rounds, default: 10)
   - TOKEN_EXPIRY (JWT expiry in hours, default: 24)
3. Users table exists with schema:
   - id (UUID, primary key)
   - email (VARCHAR unique)
   - password_hash (VARCHAR)
   - created_at (TIMESTAMP)

FULL FILE REPLACEMENT:

import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import { Pool } from 'pg';

interface User {
  id: string;
  email: string;
  password_hash: string;
  created_at: Date;
}

interface AuthToken {
  token: string;
  expiresIn: number;
}

class AuthService {
  private pool: Pool;
  private jwtSecret: string;
  private passwordRounds: number;
  private tokenExpiry: number;

  constructor(pool: Pool) {
    this.pool = pool;
    this.jwtSecret = process.env.JWT_SECRET || '';
    this.passwordRounds = parseInt(process.env.PASSWORD_ROUNDS || '10');
    this.tokenExpiry = parseInt(process.env.TOKEN_EXPIRY || '24');

    if (!this.jwtSecret || this.jwtSecret.length < 32) {
      throw new Error('JWT_SECRET not set or too short');
    }
  }

  async registerUser(
    email: string,
    password: string
  ): Promise<{ id: string; email: string }> {
    const passwordHash = await bcrypt.hash(password, this.passwordRounds);

    const result = await this.pool.query(
      'INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id, email',
      [email, passwordHash]
    );

    return result.rows[0];
  }

  async login(email: string, password: string): Promise<AuthToken> {
    const result = await this.pool.query(
      'SELECT id, password_hash FROM users WHERE email = $1',
      [email]
    );

    if (result.rows.length === 0) {
      throw new Error('User not found');
    }

    const user = result.rows[0];
    const isPasswordValid = await bcrypt.compare(password, user.password_hash);

    if (!isPasswordValid) {
      throw new Error('Invalid password');
    }

    const token = jwt.sign(
      { userId: user.id, email },
      this.jwtSecret,
      { expiresIn: `${this.tokenExpiry}h` }
    );

    return {
      token,
      expiresIn: this.tokenExpiry * 3600,
    };
  }

  async verifyToken(token: string): Promise<{ userId: string; email: string }> {
    try {
      const decoded = jwt.verify(token, this.jwtSecret) as {
        userId: string;
        email: string;
      };
      return decoded;
    } catch (err) {
      throw new Error('Invalid or expired token');
    }
  }

  async getUserById(id: string): Promise<User | null> {
    const result = await this.pool.query(
      'SELECT id, email, password_hash, created_at FROM users WHERE id = $1',
      [id]
    );

    return result.rows[0] || null;
  }
}

export default AuthService;

---

USAGE INSTRUCTIONS:

1. Installation:
   npm install bcrypt jsonwebtoken pg

2. Environment Setup:
   JWT_SECRET=your-secret-key-32-characters-minimum
   PASSWORD_ROUNDS=10
   TOKEN_EXPIRY=24
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=myapp
   DB_USER=postgres
   DB_PASSWORD=password

3. Database Schema:
   CREATE TABLE users (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     email VARCHAR UNIQUE NOT NULL,
     password_hash VARCHAR NOT NULL,
     created_at TIMESTAMP DEFAULT now()
   );

4. Usage Example:
   import { Pool } from 'pg';
   import AuthService from './services/auth.service';

   const pool = new Pool();
   const authService = new AuthService(pool);

   // Register user
   const user = await authService.registerUser('user@example.com', 'password123');

   // Login
   const { token, expiresIn } = await authService.login('user@example.com', 'password123');

   // Verify token
   const decoded = await authService.verifyToken(token);

   // Get user
   const userData = await authService.getUserById(decoded.userId);

5. Error Handling:
   All methods throw errors with descriptive messages.
   Always use try/catch blocks:

   try {
     const { token } = await authService.login(email, password);
   } catch (err) {
     console.error('Login failed:', err.message);
   }

6. Testing:
   npm test

---

NEXT STEPS:
1. Deploy to development environment
2. Run integration tests
3. Proceed to VALIDATION phase
```

---

## Phase Differences

| Aspect | Design | Implementation |
|--------|--------|-----------------|
| **Purpose** | Create architecture | Write code |
| **Options** | Multiple required | Single only |
| **Structure** | Diagrams, tradeoffs | Complete files |
| **Filename** | Not needed | Explicit required |
| **Content** | Architecture prose | Full code |
| **Allowed** | Design patterns | Code with structure |
| **Forbidden** | Code | Snippets, alternatives |
| **Next Phase** | → Implementation | → Validation |

---

## Key Principles

1. **Explicit Always** - No assumptions about file locations or existing code
2. **Complete Content** - Full file replacements, never snippets
3. **Single Path** - One implementation, no alternatives
4. **Deterministic** - Reproducible, not probabilistic
5. **Assumption Safety** - All prerequisites documented

---

## Common Mistakes

### Mistake 1: Missing Filename

```
❌ WRONG:
Here's the authentication code:

function authenticate() { }
```

```
✅ CORRECT:
File: src/auth.ts

Complete file replacement:

function authenticate() { }
```

### Mistake 2: Partial Content

```
❌ WRONG:
In database.ts, add this function:

function query(sql) {
  // implementation
}

// ... rest of file unchanged
```

```
✅ CORRECT:
File: src/database.ts

Full file replacement:

import { Pool } from 'pg';

const pool = new Pool();

function query(sql) {
  // implementation
}

export { query };
```

### Mistake 3: Multiple Options

```
❌ WRONG:
Option 1: Use Redis
Option 2: Use Memcached

I recommend Option 1, but both work.
```

```
✅ CORRECT:
Based on the design phase decision to use Redis:

File: src/cache.ts

Full file replacement:

import redis from 'redis';
// Complete Redis implementation
```

### Mistake 4: Unspecified Assumptions

```
❌ WRONG:
Make sure you have the dependencies installed.
```

```
✅ CORRECT:
ASSUMPTIONS:
1. Node.js 16+ installed
2. PostgreSQL running on localhost:5432
3. npm dependencies: pg, bcrypt (v5.0+)
4. Environment variables: DB_PASSWORD set

PREREQUISITES:
- [ ] Database configured
- [ ] npm install completed
```

---

## Testing

Test the implementation phase enforcement:

```python
from lathe_tool import lathe_plan, lathe_validate

# Step 1: Plan implementation phase
plan = lathe_plan(
    project="myapp",
    scope="authentication",
    phase="implementation",
    goal="Implement user authentication"
)

# Output without filename (should FAIL)
bad_output = """
Here's the auth service:

function login(email, password) {
  return verify(email, password);
}
"""

result = lathe_validate(phase="implementation", output=bad_output)
assert result["status"] == "fail"  # Filename missing

# Output with partial content (should FAIL)
bad_output2 = """
File: src/auth.ts

Add this function:

function login() { }

// ... rest of file
"""

result = lathe_validate(phase="implementation", output=bad_output2)
assert result["status"] == "fail"  # Partial content

# Output with alternatives (should FAIL)
bad_output3 = """
File: src/auth.ts

Option 1: JWT authentication
Option 2: Session authentication

I recommend Option 1.
"""

result = lathe_validate(phase="implementation", output=bad_output3)
assert result["status"] == "fail"  # Multiple options

# Good output with filename, full content, single approach (should PASS)
good_output = """
File: src/auth.ts

ASSUMPTIONS:
- PostgreSQL configured
- JWT_SECRET environment variable set

Full file replacement:

export class AuthService {
  login(email: string, password: string) {
    // Complete implementation
  }
}
"""

result = lathe_validate(phase="implementation", output=good_output)
assert result["status"] in ["pass", "warn"]  # Valid implementation
```

---

## Integration with OpenWebUI

When using the Lathe tool in OpenWebUI:

1. **User requests implementation:** "Implement the authentication service based on the design"

2. **lathe_plan called:**
   - Returns system prompt with implementation requirements
   - Includes strict validation rules
   - Emphasizes complete, explicit output

3. **LLM generates implementation:**
   - Specifies exact filename
   - Provides complete file content
   - Documents all assumptions
   - Single, clear approach

4. **lathe_validate called:**
   - Validates filename is present → MUST PASS
   - Validates full content (no snippets) → MUST PASS
   - Validates no alternatives → MUST PASS
   - Validates assumptions documented → WARNS if missing

5. **OpenWebUI displays result:**
   - Shows validation status
   - Lists any warnings about assumptions
   - Can proceed to VALIDATION phase

---

## Safety Constraints

Implementation phase is **safe by constraint:**

❌ **Does NOT:**
- Execute code
- Auto-fix errors
- Write to disk
- Create transactions
- Modify system state

✅ **Only:**
- Validates output format
- Returns analysis
- Provides user-facing text

---

## Support

- **Implementation:** `lathe/validation/rules.py` → Implementation rules
- **Enforcement:** `lathe_tool.py` and `lathe/tool/wrapper.py`
- **Testing:** `tests/test_tool_wrapper.py`
- **Phase Discipline:** Implementation phase enforces complete, explicit, safe outputs

---

**Status:** ✅ Implemented and enforced
**Severity:** All FAIL (critical for reproducibility)
**Default:** Enabled for all implementation phase operations

---

## Next Phase

After implementation is complete:
- **→ VALIDATION phase** - Test and verify implementation
- Implementation becomes input to validation
- Cycle back to design/implementation if issues found
