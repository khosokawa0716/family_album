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
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        React: "readonly",
        console: "readonly",
        window: "readonly",
        document: "readonly",
        sessionStorage: "readonly",
        localStorage: "readonly",
        alert: "readonly",
        globalThis: "readonly",
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
        React: "readonly",
        console: "readonly",
        window: "readonly",
        document: "readonly",
        sessionStorage: "readonly",
        localStorage: "readonly",
        alert: "readonly",
        globalThis: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "warn",
    },
  },
  js.configs.recommended,
];
