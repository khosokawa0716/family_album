import js from "@eslint/js";
import parser from "@typescript-eslint/parser";
import globals from "globals";

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
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        ...globals.browser,
        ...globals.node,
        React: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "warn",
    },
  },
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
        React: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "warn",
    },
  },
  js.configs.recommended,
];
