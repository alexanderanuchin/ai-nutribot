import tseslint from 'typescript-eslint'

const colorLiteralMessage =
  'Используйте дизайн-токены через CSS custom properties вместо хардкодных цветов.'

export default [
  {
    ignores: ['dist', 'node_modules'],
  },
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: { jsx: true },
      },
    },
  },
  {
    files: ['src/components/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector: "Literal[value=/^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$/]",
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
          selector: 'TemplateLiteral[expressions.length=0][quasis.0.value.raw=/#[0-9A-Fa-f]{3,8}/]',
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

