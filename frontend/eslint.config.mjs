import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import globals from 'globals'
import tseslint from 'typescript-eslint'

const colorLiteralMessage =
  'Используйте дизайн-токены через CSS custom properties вместо хардкодных цветов.'

export default [
  {
    ignores: ['dist', 'node_modules'],
  },
  {
    files: ['**/*.{ts,tsx,js,jsx}'],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.jest,
        ...globals.vitest,
      },
    },
    plugins: {
      '@typescript-eslint': tseslint.plugin,
      react,
      'react-hooks': reactHooks,
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
    rules: {
      'react/jsx-uses-react': 'off',
      'react/react-in-jsx-scope': 'off',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'off',
    },
  },
  {
    files: ['src/components/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector:
            "Literal[value=/^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$/]",
          message: colorLiteralMessage,
        },
        {
          selector: "Literal[value=/^rgba?\\(/i]",
          message: colorLiteralMessage,
        },
        {
          selector: "Literal[value=/^hsla?\\(/i]",
          message: colorLiteralMessage,
        },
        {
          selector:
            'TemplateLiteral[expressions.length=0][quasis.0.value.raw=/#[0-9A-Fa-f]{3,8}/]',
          message: colorLiteralMessage,
        },
        {
          selector: 'TemplateLiteral[expressions.length=0][quasis.0.value.raw=/rgba?\\(/i]',
          message: colorLiteralMessage,
        },
        {
          selector: 'TemplateLiteral[expressions.length=0][quasis.0.value.raw=/hsla?\\(/i]',
          message: colorLiteralMessage,
        },
      ],
    },
  },
]
