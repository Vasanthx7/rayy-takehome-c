import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { OrderSummary } from "./OrderSummary";
import type { Order } from "./types";

const baseOrder: Order = {
  order_id: "ord_test_1",
  subtotal_paise: 38997,
  total_paise: 38997,
  status: "pending",
  discount: null,
};

const discountedOrder: Order = {
  ...baseOrder,
  total_paise: 31978,
  discount: { code: "KIDS18", amount_paise: 7019 },
};

function deferred() {
  let resolve!: () => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<void>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("OrderSummary", () => {
  it("renders", () => {
    render(<OrderSummary order={baseOrder} onPay={async () => {}} />);
    expect(screen.getByRole("region", { name: "Order summary" })).toBeInTheDocument();
  });

  it("shows subtotal and total through formatPaise", () => {
    render(<OrderSummary order={discountedOrder} onPay={async () => {}} />);
    expect(screen.getByText("₹389.97")).toBeInTheDocument(); // subtotal
    expect(screen.getByText("₹319.78")).toBeInTheDocument(); // total
  });

  it("shows the discount code and amount when there is one", () => {
    render(<OrderSummary order={discountedOrder} onPay={async () => {}} />);
    expect(screen.getByText("Discount · KIDS18")).toBeInTheDocument();
    expect(screen.getByText("−₹70.19")).toBeInTheDocument();
  });

  it("omits the discount when there is none", () => {
    render(<OrderSummary order={baseOrder} onPay={async () => {}} />);
    expect(screen.queryByText(/Discount/)).not.toBeInTheDocument();
    expect(screen.queryByText(/You save/)).not.toBeInTheDocument();
  });

  it("reads 'Paid' and stays disabled when the order is paid", () => {
    render(<OrderSummary order={{ ...baseOrder, status: "paid" }} onPay={async () => {}} />);
    const button = screen.getByRole("button", { name: "Paid" });
    expect(button).toBeDisabled();
  });

  it("shows a loader and disables the button while paying, still reading 'Pay'", async () => {
    const user = userEvent.setup();
    const d = deferred();
    const onPay = vi.fn(() => d.promise);
    render(<OrderSummary order={baseOrder} onPay={onPay} />);

    await user.click(screen.getByRole("button", { name: "Pay" }));
    expect(onPay).toHaveBeenCalledTimes(1);

    const button = screen.getByRole("button", { name: "Pay" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button.querySelector(".slip__spinner")).not.toBeNull();

    d.resolve();
    await waitFor(() => expect(button).toBeEnabled());
    expect(button).toHaveAttribute("aria-busy", "false");
    expect(button.querySelector(".slip__spinner")).toBeNull();
  });

  it("shows an alert on failure and allows retry", async () => {
    const user = userEvent.setup();
    const onPay = vi
      .fn<() => Promise<void>>()
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce(undefined);
    render(<OrderSummary order={baseOrder} onPay={onPay} />);

    await user.click(screen.getByRole("button", { name: "Pay" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Payment failed/i);
    expect(screen.getByRole("button", { name: "Pay" })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: "Pay" }));
    expect(onPay).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
  });
});
