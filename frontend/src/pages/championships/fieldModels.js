import { computed, reactive } from 'vue'

/**
 * Exposes each listed field of an object v-model as a writable property, so
 * templates can `v-model="fields.name"`. Every write emits a new object; the
 * parent's form is never mutated in place.
 * @param {import('vue').Ref<Record<string, any>>} model ref from defineModel()
 * @param {string[]} keys
 */
export function useFieldModels(model, keys) {
  return reactive(Object.fromEntries(keys.map((key) => [key, computed({
    get: () => model.value?.[key],
    set: (value) => {
      model.value = { ...model.value, [key]: value }
    }
  })])))
}
