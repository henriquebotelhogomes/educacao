import { FlatCompat } from "@eslint/eslintrc";
import { globalIgnores } from "eslint/config";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const directory = dirname(fileURLToPath(import.meta.url));
const compat = new FlatCompat({ baseDirectory: directory });
const config = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  globalIgnores([".next/**", "next-env.d.ts", "node_modules/**"])
];

export default config;
