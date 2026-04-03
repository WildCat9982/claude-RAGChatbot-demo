import js from "@eslint/js";

export default [
    js.configs.recommended,
    {
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: "script",
            globals: {
                document: "readonly",
                window: "readonly",
                console: "readonly",
                fetch: "readonly",
                Date: "readonly",
                marked: "readonly",
            },
        },
        rules: {
            "no-unused-vars": "warn",
            "no-console": "off",
            eqeqeq: ["error", "always"],
            "no-var": "error",
            "prefer-const": "warn",
        },
    },
];