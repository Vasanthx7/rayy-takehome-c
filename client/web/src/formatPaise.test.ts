import { describe, expect, it } from "vitest";
import { formatPaise } from "./formatPaise";

describe("formatPaise", () => {
  it("formats the README examples", () => {
    expect(formatPaise(199999)).toBe("₹1,999.99");
    expect(formatPaise(12345678)).toBe("₹1,23,456.78");
    expect(formatPaise(5)).toBe("₹0.05");
    expect(formatPaise(0)).toBe("₹0.00");
  });

  it("uses Indian digit grouping for large amounts", () => {
    expect(formatPaise(1234567890)).toBe("₹1,23,45,678.90");
  });

  it("formats a negative amount with a leading minus", () => {
    expect(formatPaise(-199999)).toBe("₹-1,999.99");
    expect(formatPaise(-5)).toBe("₹-0.05");
  });

  it("throws on a non-integer", () => {
    expect(() => formatPaise(1.5)).toThrow();
    expect(() => formatPaise(100.01)).toThrow();
  });
});
