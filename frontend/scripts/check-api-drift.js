import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const openapiPath = path.resolve(root, "../contracts/openapi.json");
const targetPath = path.resolve(root, "src/api/schema.d.ts");
const tmpPath = path.resolve(root, "src/api/.tmp_schema.d.ts");

try {
  execSync(`npx openapi-typescript "${openapiPath}" -o "${tmpPath}"`, {
    cwd: root,
    stdio: "pipe",
  });

  const generated = fs.readFileSync(tmpPath, "utf-8");
  const existing = fs.existsSync(targetPath) ? fs.readFileSync(targetPath, "utf-8") : "";

  if (generated !== existing) {
    console.error("Error: OpenAPI generated schema has drifted from src/api/schema.d.ts.");
    console.error("Run 'npm run api:generate' to update the generated types.");
    process.exit(1);
  }

  console.log("✓ OpenAPI schema types are up to date.");
} finally {
  if (fs.existsSync(tmpPath)) {
    fs.unlinkSync(tmpPath);
  }
}
