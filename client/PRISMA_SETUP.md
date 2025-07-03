# Prisma ORM Setup for SQL Server

## Overview

Drizzle ORM has been replaced with **Prisma ORM**, which has excellent SQL Server support and TypeScript integration.

## What's Been Done

1. ✅ Uninstalled Drizzle ORM packages (`drizzle-orm`, `drizzle-kit`)
2. ✅ Uninstalled legacy SQL packages (`mssql`, `@types/mssql`, `odbc`)
3. ✅ Installed Prisma ORM (`prisma`, `@prisma/client`)
4. ✅ Configured Prisma schema for SQL Server
5. ✅ Updated database service to use Prisma (removed config dependency)
6. ✅ Updated data service factory (simplified)
7. ✅ Generated Prisma client
8. ✅ Removed unused files:
   - `src/electron/main/config/database.ts`
   - `src/electron/main/config/` directory (now empty)

## Next Steps

### 1. Configure Database Connection

Create a `.env` file in the root directory with your SQL Server configuration:

```env
# Authentication Type: "sql", "windows", or "azure"
DB_AUTH_TYPE=sql

# Common Database Settings
DB_SERVER=localhost
DB_PORT=1433
DB_NAME=your_database
DB_ENCRYPT=true
DB_TRUST_SERVER_CERTIFICATE=true

# For SQL Server Authentication (DB_AUTH_TYPE=sql)
DB_USER=your_username
DB_PASSWORD=your_password

# For Windows Authentication (DB_AUTH_TYPE=windows)
# No username/password needed - uses integrated security
# DB_AUTH_TYPE=windows

# For Azure SQL Database (DB_AUTH_TYPE=azure)
# DB_AUTH_TYPE=azure
# DB_SERVER=your-server.database.windows.net
# DB_AZURE_USER=your_azure_username
# DB_AZURE_PASSWORD=your_azure_password
# DB_AZURE_CLIENT_ID=your_client_id (optional)
# DB_ENCRYPT=true
# DB_TRUST_SERVER_CERTIFICATE=false
```

### 2. Update Prisma Schema

Edit `prisma/schema.prisma` to match your actual database tables:

```prisma
// Example: Replace the User model with your actual tables
model EtoRunLog {
  id         Int      @id @default(autoincrement())
  runId      Int?
  receivedTs DateTime?
  // Add your other columns here

  @@map("EtoRunLog") // Maps to your actual table name
}
```

### 3. Introspect Existing Database (Optional)

If you have an existing database, you can automatically generate models:

```bash
npx prisma db pull
```

This will update your schema.prisma file with your existing database structure.

### 4. Generate Client After Schema Changes

After updating your schema, regenerate the client:

```bash
npx prisma generate
```

### 5. Database Migrations (Optional)

If you want to manage database changes with Prisma:

```bash
# Create and apply migrations
npx prisma migrate dev --name init
```

## Alternative ORMs Considered

If Prisma doesn't meet your needs, here are other SQL Server-compatible options:

### 2. **TypeORM**

```bash
npm install typeorm mssql @types/mssql
```

- Decorator-based ORM
- Good SQL Server support
- More traditional ORM approach

### 3. **Sequelize**

```bash
npm install sequelize mssql
npm install --save-dev @types/sequelize
```

- Mature ORM with SQL Server support
- Promise-based API

### 4. **MikroORM**

```bash
npm install @mikro-orm/core @mikro-orm/mssql
```

- Modern TypeScript ORM
- Good performance

### 5. **Raw SQL with mssql package**

```bash
npm install mssql @types/mssql
```

- Direct SQL queries
- Maximum control and performance

## Why Prisma is Recommended

1. **Excellent TypeScript Support**: Auto-generated types from schema
2. **Great Developer Experience**: Intuitive API and excellent tooling
3. **SQL Server Support**: First-class support for SQL Server
4. **Schema Management**: Easy migrations and introspection
5. **Performance**: Efficient query generation
6. **Documentation**: Comprehensive docs and community
7. **Simplified Configuration**: Uses environment variables instead of config objects

## Usage Examples

```typescript
import { prisma } from "./database/prisma-client";

// Type-safe queries
const users = await prisma.user.findMany({
  where: {
    email: {
      contains: "@example.com",
    },
  },
});

// Raw SQL when needed
const result = await prisma.$queryRaw`
  SELECT * FROM EtoRunLog 
  WHERE receivedTs > ${new Date()}
`;
```

## Build Configuration

The setup includes proper build configuration to ensure Prisma works in production:

- **`scripts/copy-prisma.mjs`** - Script to copy generated Prisma files to build directory
- **`package.json`** - Updated build scripts:
  - `prisma:generate` - Generates Prisma client
  - `copy:prisma` - Copies generated files to build
  - `transpile:electron` - Now includes Prisma generation and copying
- **`src/electron/main/tsconfig.json`** - Includes generated files in compilation

The build process now:

1. Generates Prisma client (`prisma generate`)
2. Compiles TypeScript (`tsc`)
3. Copies Prisma files to build directory (`copy:prisma`)

**Note**: You may see warnings about skipping locked files (like `query_engine-windows.dll.node`) during the copy step. This is normal and safe - these files are already in the build directory from previous runs.

## Files Modified/Removed

- ✅ `src/electron/main/services/database-service.ts` - Updated to use Prisma
- ✅ `src/electron/main/services/data-service-factory.ts` - Simplified (no config needed)
- ✅ `src/electron/main/database/prisma-client.ts` - New Prisma client service with auth types
- ✅ `prisma/schema.prisma` - Prisma schema configuration
- ✅ `src/electron/main/tsconfig.json` - Updated to include generated files
- ✅ `package.json` - Dependencies and build scripts updated
- ✅ `scripts/copy-prisma.mjs` - **NEW** build script for copying Prisma files
- ❌ `src/electron/main/config/database.ts` - **REMOVED** (replaced by .env)
- ❌ `src/electron/main/config/` directory - **REMOVED** (empty)

## Removed Packages

- `drizzle-orm`
- `drizzle-kit`
- `mssql`
- `@types/mssql`
- `odbc`

The codebase is now cleaner and uses modern Prisma ORM with environment-based configuration!
