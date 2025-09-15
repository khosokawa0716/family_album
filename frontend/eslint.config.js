import js from "@eslint/js";
import parser from "@typescript-eslint/parser";

export default [
  {
    ignores: ["node_modules/", "dist/", ".next/", "coverage/", "*.config.js"],
  },
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser,
      parserOptions: {
        project: "./tsconfig.json",
        sourceType: "module",
        ecmaVersion: "latest",
      },
    },
    rules: {
      // 必要に応じてルール追加
      "no-unused-vars": "warn",
    },
  },
  {
    files: ["**/*.{js,jsx}"],
    rules: {
      "no-unused-vars": "warn",
    },
  },
  js.configs.recommended,
];
