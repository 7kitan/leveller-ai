import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a number with fixed decimal places, avoiding floating-point precision issues
 * @param value - The number to format
 * @param decimals - Number of decimal places (default: 1)
 * @returns Formatted number as string
 */
export function formatNumber(value: number | null | undefined, decimals: number = 1): string {
  if (value == null || isNaN(value)) return '0';
  return Number(value.toFixed(decimals)).toString();
}

/**
 * Format a percentage value with fixed decimal places
 * @param value - The percentage value (e.g., 42.4 for 42.4%)
 * @param decimals - Number of decimal places (default: 1)
 * @returns Formatted percentage string (e.g., "42.4%")
 */
export function formatPercent(value: number | null | undefined, decimals: number = 1): string {
  if (value == null || isNaN(value)) return '0%';
  return `${Number(value.toFixed(decimals))}%`;
}

/**
 * Format currency with proper decimal handling
 * @param value - The currency value
 * @param currency - Currency symbol (default: '$')
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted currency string
 */
export function formatCurrency(value: number | null | undefined, currency: string = '$', decimals: number = 2): string {
  if (value == null || isNaN(value)) return `${currency}0`;
  return `${currency}${Number(value.toFixed(decimals))}`;
}

/**
 * Format Vietnamese salary in millions (VND)
 * @param value - Salary value in VND
 * @param decimals - Number of decimal places (default: 0 for whole millions)
 * @returns Formatted salary string (e.g., "42M")
 */
export function formatSalaryVND(value: number | null | undefined, decimals: number = 0): string {
  if (value == null || isNaN(value)) return '0M';
  const millions = value / 1000000;
  return `${Number(millions.toFixed(decimals))}M`;
}

/**
 * Format hours with decimal precision
 * @param value - Hours value
 * @param decimals - Number of decimal places (default: 1)
 * @returns Formatted hours string (e.g., "42.5h")
 */
export function formatHours(value: number | null | undefined, decimals: number = 1): string {
  if (value == null || isNaN(value)) return '0h';
  return `${Number(value.toFixed(decimals))}h`;
}
