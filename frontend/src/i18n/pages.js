import { mergeMessages } from './merge'

// Each redesigned page keeps its copy in src/i18n/pages/<page>.js
// (default export { ru: {...}, en: {...} }); they are merged here automatically.
const modules = import.meta.glob('./pages/*.js', { eager: true })

export const pageMessages = mergeMessages({}, ...Object.values(modules).map((module) => module.default))
