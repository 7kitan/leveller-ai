"use client";

import React, { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface DebouncedInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement | HTMLTextAreaElement>, "onChange"> {
  value: string;
  onChange: (value: string) => void;
  debounce?: number;
  isTextarea?: boolean;
}

export const DebouncedInput: React.FC<DebouncedInputProps> = ({
  value: initialValue,
  onChange,
  debounce = 500,
  isTextarea = false,
  className,
  ...props
}) => {
  const [value, setValue] = useState(initialValue);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    setValue(initialValue);
  }, [initialValue]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setValue(newValue);

    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    timerRef.current = setTimeout(() => {
      onChange(newValue);
    }, debounce);
  };

  // Ensure we sync the final value on blur to avoid losing data
  const handleBlur = (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    onChange(value);
    if (props.onBlur) {
      props.onBlur(e as any);
    }
  };

  const Component = isTextarea ? "textarea" : "input";

  return (
    <Component
      {...props as any}
      value={value}
      onChange={handleChange}
      onBlur={handleBlur}
      className={className}
    />
  );
};
