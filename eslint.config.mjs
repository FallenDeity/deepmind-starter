// @ts-check

import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';

const __dirname = new URL('.', import.meta.url).pathname;

export default tseslint.config(
  eslint.configs.recommended,
  tseslint.configs.strictTypeChecked,
  tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: {
		project: './tsconfig.json',
        projectService: true,
        tsconfigRootDir: __dirname,
      },
    },
	rules: {
		"no-constructor-return": "error",
		"no-duplicate-imports": "error",
		"@typescript-eslint/no-unused-vars": "off",
		"@typescript-eslint/no-require-imports": "off",

		// Suggestion rules
		"arrow-body-style": ["error", "as-needed"],
		"complexity": ["error", 15],
		"consistent-return": "error",
		"curly": ["error", "multi-line"],
		"dot-notation": "error",
		"eqeqeq": ["error", "always"],
		"no-empty-function": "error",
		"no-eval": "error",
		"no-var": "error",
		"prefer-const": "error",
		"prefer-destructuring": ["error", { "object": true, "array": false }],
		"prefer-rest-params": "error",
		"prefer-spread": "error",
		"prefer-template": "error",
	}
  },
);
