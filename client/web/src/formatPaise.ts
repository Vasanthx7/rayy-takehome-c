/**
 * Format integer paise as rupees: en-IN digit grouping, exactly two decimals,
 * integer maths only (no floating-point division of the amount).
 *
 *   formatPaise(199999)   === "₹1,999.99"
 *   formatPaise(12345678) === "₹1,23,456.78"
 *   formatPaise(5)        === "₹0.05"
 *   formatPaise(0)        === "₹0.00"
 *
 * Throws an Error if `paise` is not an integer.
 */
export function formatPaise(paise: number): string {
  if (!Number.isInteger(paise)) {
    throw new Error(`formatPaise expects an integer number of paise, got ${paise}`);
  }

  const sign = paise < 0 ? "-" : "";
  const abs = Math.abs(paise);
  const rupees = Math.floor(abs / 100);
  const remainder = abs % 100; // exact for safe integers; no fractional rounding

  // en-IN grouping: last three digits, then the rest in pairs.
  const digits = String(rupees);
  const lastThree = digits.slice(-3);
  const rest = digits.slice(0, -3);
  const grouped = rest
    ? rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," + lastThree
    : lastThree;

  return `₹${sign}${grouped}.${String(remainder).padStart(2, "0")}`;
}
