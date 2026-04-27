"use client";

import React, { useState, useEffect, useRef } from "react";
import { ChevronDown, Check } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import styles from "./custom-dropdown.module.css";

interface CustomDropdownProps {
  value: string;
  options: { label: string; value: string }[] | string[];
  onChange: (val: string) => void;
  placeholder?: string;
  className?: string;
  buttonClassName?: string;
  style?: React.CSSProperties;
}

const CustomDropdown: React.FC<CustomDropdownProps> = ({
  value,
  options,
  onChange,
  placeholder,
  className,
  buttonClassName,
  style,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const getOptionLabel = (opt: any) => (typeof opt === "string" ? opt : opt.label);
  const getOptionValue = (opt: any) => (typeof opt === "string" ? opt : opt.value);

  const selectedOption = options.find((opt) => getOptionValue(opt) === value);
  const displayLabel = selectedOption ? getOptionLabel(selectedOption) : value || placeholder;

  return (
    <div 
      className={cn(styles.customDropdownContainer, isOpen && styles.customDropdownContainerActive, className)} 
      ref={dropdownRef}
    >
      <button
        type="button"
        className={cn(styles.customDropdownButton, buttonClassName, isOpen && styles.customDropdownButtonActive)}
        onClick={() => setIsOpen(!isOpen)}
        style={style}
      >
        <span className="truncate">{displayLabel}</span>
        <ChevronDown size={14} className={cn(styles.dropdownChevron, isOpen && styles.dropdownChevronRotate)} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.98 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className={styles.customDropdownMenu}
          >
            {options.map((opt) => {
              const optVal = getOptionValue(opt);
              const optLabel = getOptionLabel(opt);
              const isActive = optVal === value;
              
              return (
                <button
                  key={optVal}
                  type="button"
                  className={cn(
                    styles.customDropdownOption,
                    isActive && styles.customDropdownOptionActive
                  )}
                  onClick={() => {
                    onChange(optVal);
                    setIsOpen(false);
                  }}
                >
                  <span className="truncate">{optLabel}</span>
                  {isActive && <Check size={12} className={styles.optionCheck} />}
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CustomDropdown;
