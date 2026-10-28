import React, { useEffect, useRef, useState } from "react";

type RevealProps = {
  children: React.ReactNode;
  as?: keyof React.JSX.IntrinsicElements;
  className?: string;
  /** Delay in ms, for staggering items that enter together */
  delay?: number;
  /** Fraction of the element that must be on screen to count as visible */
  threshold?: number;
} & Omit<React.HTMLAttributes<HTMLElement>, "className" | "children">;

/**
 * Fades its content in when it scrolls into view and out again when it scrolls away,
 * in either direction. Content stays fully visible for reduced-motion users and in
 * browsers without IntersectionObserver.
 */
export const Reveal: React.FC<RevealProps> = ({
  children,
  as = "div",
  className = "",
  delay = 0,
  threshold = 0.15,
  style,
  ...rest
}) => {
  const ref = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting), {
      threshold,
      rootMargin: "0px 0px -8% 0px",
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);

  const Tag = as as React.ElementType;
  return (
    <Tag
      ref={ref}
      className={`reveal ${visible ? "is-visible" : ""} ${className}`}
      style={delay ? { transitionDelay: `${delay}ms`, ...style } : style}
      {...rest}
    >
      {children}
    </Tag>
  );
};

export default Reveal;
