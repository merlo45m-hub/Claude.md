import tsparser from "@typescript-eslint/parser";
import { defineConfig } from "eslint/config";
import obsidianmd from "eslint-plugin-obsidianmd";
import globals from "globals";

// Matches the default configuration the Obsidian submission bot uses — no
// custom brands or acronyms, so what passes locally also passes their scan.
export default defineConfig([
  {
    ignores: ["tests/**", "node_modules/**", "main.js"],
  },
  ...obsidianmd.configs.recommended,
  {
    files: ["**/*.ts"],
    languageOptions: {
      parser: tsparser,
      parserOptions: { project: "./tsconfig.json" },
      globals: { ...globals.browser, ...globals.node },
    },
  },
]);
