import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Pipeline de vídeo (Python/Blender), fora do app:
    "tool/**",
    "research/**",
    "mixamo/**",
    "videos/**",
    "exercises/**",
    "clinical_tests/**",
  ]),
]);

export default eslintConfig;
