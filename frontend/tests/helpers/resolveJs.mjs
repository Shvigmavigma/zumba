// Test-only resolver: Vite allows extensionless relative imports ("./api"),
// Node ESM does not. Retry such specifiers with ".js".
export async function resolve(specifier, context, nextResolve) {
  try {
    return await nextResolve(specifier, context)
  } catch (error) {
    if (error?.code === 'ERR_MODULE_NOT_FOUND' && /^\.{1,2}\//.test(specifier) && !/\.\w+$/.test(specifier)) {
      return nextResolve(`${specifier}.js`, context)
    }
    throw error
  }
}
