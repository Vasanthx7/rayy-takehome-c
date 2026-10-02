import { useState } from "react";
import { formatPaise } from "./formatPaise";
import type { Order } from "./types";
import "./OrderSummary.css";

/**
 * Shows the subtotal, the discount (code and amount) when there is one, and
 * the total, all through formatPaise, plus a "Pay" button that calls onPay.
 *
 * - The button is disabled while onPay is pending (no double submit); it
 *   still reads "Pay".
 * - Only when order.status is "paid" does the button read "Paid"; it is then
 *   disabled.
 * - If onPay rejects, show an error in an element with role="alert" and
 *   re-enable the button.
 */
export function OrderSummary(props: { order: Order; onPay: () => Promise<void> }): JSX.Element {
  const { order, onPay } = props;
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);
  const isPaid = order.status === "paid";

  async function handlePay() {
    setFailed(false);
    setPending(true);
    try {
      await onPay();
    } catch {
      setFailed(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="slip" aria-label="Order summary">
      <header className="slip__head">
        <h2 className="slip__order">Order {order.order_id}</h2>
      </header>

      <dl className="slip__lines">
        <div className="slip__line">
          <dt>Subtotal</dt>
          <dd className="slip__figure">{formatPaise(order.subtotal_paise)}</dd>
        </div>
        {order.discount && (
          <div className="slip__line">
            <dt>Discount · {order.discount.code}</dt>
            <dd className="slip__figure slip__figure--save">
              −{formatPaise(order.discount.amount_paise)}
            </dd>
          </div>
        )}
      </dl>

      <div className="slip__perforation" role="presentation" />

      <div className="slip__line slip__line--total">
        <span>Total</span>
        <span className="slip__figure slip__total">{formatPaise(order.total_paise)}</span>
      </div>

      {order.discount && (
        <p className="slip__save">
          You save {formatPaise(order.discount.amount_paise)} with {order.discount.code}
        </p>
      )}

      <button
        type="button"
        className="slip__pay"
        onClick={handlePay}
        disabled={isPaid || pending}
        aria-busy={pending}
        data-state={isPaid ? "paid" : pending ? "pending" : "ready"}
      >
        {pending && <span className="slip__spinner" aria-hidden="true" />}
        {isPaid ? "Paid" : "Pay"}
      </button>

      {failed && (
        <div className="slip__alert" role="alert">
          Payment failed. Please try again.
        </div>
      )}
    </section>
  );
}
