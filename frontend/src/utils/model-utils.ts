import type { Model } from '@/types/models';

export function getLastModelOfVendor(models: { [key: string]: { [key: string]: Model } }, vendor: string): Model | undefined {
  const vendorModels = models[vendor];
  if (!vendorModels) {
    throw new Error(`Vendor ${vendor} not found`);
  }

  const modelKeys = Object.keys(vendorModels);
  if (modelKeys.length === 0) {
    throw new Error(`No models found for vendor ${vendor}`);
  }

  const lastModelKey = modelKeys[modelKeys.length - 1];
  return vendorModels[lastModelKey];
}
