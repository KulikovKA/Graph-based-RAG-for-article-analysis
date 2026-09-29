import tseslint from 'typescript-eslint';
import react from 'eslint-plugin-react';

export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  ...tseslint.configs.recommended,
  { files: ['**/*.{ts,tsx}'], plugins: { react }, rules: { 'no-unused-vars': 'off' } },
];
