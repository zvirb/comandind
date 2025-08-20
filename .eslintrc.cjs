module.exports = {
    "env": {
        "browser": true,
        "es2021": true,
        "node": true,
        "jest": true
    },
    "extends": [
        "eslint:recommended",
        "plugin:@typescript-eslint/recommended"
    ],
    "parser": "@typescript-eslint/parser",
    "parserOptions": {
        "ecmaVersion": "latest",
        "sourceType": "module"
    },
    "plugins": [
        "@typescript-eslint"
    ],
    "rules": {
        "indent": [
            "warn",
            4
        ],
        "linebreak-style": [
            "error",
            "unix"
        ],
        "quotes": [
            "warn",
            "double"
        ],
        "semi": [
            "warn",
            "always"
        ],
        // This is a JS project with TS type-checking, so some TS rules are not applicable
        "@typescript-eslint/no-var-requires": "off",
        "@typescript-eslint/no-explicit-any": "warn",
        "no-undef": "warn"
    },
    "ignorePatterns": ["dist/", "node_modules/", "vite.config.js", "vite.config.prod.js", "mcp_servers/"]
};
