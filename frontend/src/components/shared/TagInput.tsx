"use client";

import React, { useState, useEffect, useRef } from "react";
import { X, Tag, Plus, Loader2 } from "lucide-react";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import styles from "./TagInput.module.css";

interface Skill {
  id: string;
  name: string;
  category: string | null;
}

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  maxTags?: number;
  disabled?: boolean;
}

const TagInput: React.FC<TagInputProps> = ({
  value = [],
  onChange,
  placeholder = "Type to search or add skills...",
  maxTags = 20,
  disabled = false
}) => {
  const [inputValue, setInputValue] = useState("");
  const [suggestions, setSuggestions] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch suggestions from master skills
  useEffect(() => {
    const fetchSuggestions = async () => {
      if (!inputValue.trim() || inputValue.length < 2) {
        setSuggestions([]);
        return;
      }

      setLoading(true);
      try {
        const res = await api.get(`/admin/skills?search=${encodeURIComponent(inputValue)}&limit=10`);
        const skills = res.data.skills || [];
        
        // Filter out already selected skills
        const filtered = skills.filter(
          (skill: Skill) => !value.some(v => v.toLowerCase() === skill.name.toLowerCase())
        );
        
        setSuggestions(filtered);
        setShowDropdown(true);
      } catch (err) {
        console.error("Failed to fetch skills", err);
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
    };

    const timer = setTimeout(fetchSuggestions, 300);
    return () => clearTimeout(timer);
  }, [inputValue, value]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setShowDropdown(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleAddTag = (tag: string) => {
    const trimmed = tag.trim();
    if (!trimmed) return;
    
    // Check if already exists (case-insensitive)
    if (value.some(v => v.toLowerCase() === trimmed.toLowerCase())) {
      return;
    }

    // Check max tags limit
    if (value.length >= maxTags) {
      return;
    }

    onChange([...value, trimmed]);
    setInputValue("");
    setSuggestions([]);
    setShowDropdown(false);
    setSelectedIndex(-1);
  };

  const handleRemoveTag = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      
      if (selectedIndex >= 0 && suggestions[selectedIndex]) {
        // Select from suggestions
        handleAddTag(suggestions[selectedIndex].name);
      } else if (inputValue.trim()) {
        // Add new skill (will go to pending)
        handleAddTag(inputValue);
      }
    } else if (e.key === "Escape") {
      setShowDropdown(false);
      setSelectedIndex(-1);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex(prev => 
        prev < suggestions.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : -1));
    } else if (e.key === "Backspace" && !inputValue && value.length > 0) {
      // Remove last tag when backspace on empty input
      handleRemoveTag(value.length - 1);
    }
  };

  const exactMatch = suggestions.find(
    s => s.name.toLowerCase() === inputValue.toLowerCase()
  );

  const showCreateOption = inputValue.trim().length >= 2 && !exactMatch;

  return (
    <div className={cn(styles.container, disabled && styles.disabled)}>
      {/* Selected Tags */}
      <div className={styles.tagsContainer}>
        {value.map((tag, index) => (
          <div key={index} className={styles.tag}>
            <Tag size={12} className={styles.tagIcon} />
            <span className={styles.tagText}>{tag}</span>
            {!disabled && (
              <button
                type="button"
                onClick={() => handleRemoveTag(index)}
                className={styles.removeBtn}
                aria-label={`Remove ${tag}`}
              >
                <X size={12} />
              </button>
            )}
          </div>
        ))}

        {/* Input */}
        {!disabled && value.length < maxTags && (
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => inputValue.length >= 2 && setShowDropdown(true)}
            placeholder={value.length === 0 ? placeholder : ""}
            className={styles.input}
            disabled={disabled}
            maxLength={200}
          />
        )}
      </div>

      {/* Dropdown Suggestions */}
      {showDropdown && !disabled && (
        <div ref={dropdownRef} className={styles.dropdown}>
          {loading ? (
            <div className={styles.dropdownItem}>
              <Loader2 size={16} className={styles.spinner} />
              <span>Searching...</span>
            </div>
          ) : (
            <>
              {suggestions.map((skill, index) => (
                <button
                  key={skill.id}
                  type="button"
                  onClick={() => handleAddTag(skill.name)}
                  className={cn(
                    styles.dropdownItem,
                    selectedIndex === index && styles.dropdownItemSelected
                  )}
                >
                  <Tag size={14} className={styles.dropdownIcon} />
                  <div className={styles.dropdownContent}>
                    <span className={styles.dropdownName}>{skill.name}</span>
                    {skill.category && (
                      <span className={styles.dropdownCategory}>{skill.category}</span>
                    )}
                  </div>
                </button>
              ))}

              {showCreateOption && (
                <button
                  type="button"
                  onClick={() => handleAddTag(inputValue)}
                  className={cn(
                    styles.dropdownItem,
                    styles.dropdownItemCreate,
                    selectedIndex === suggestions.length && styles.dropdownItemSelected
                  )}
                >
                  <Plus size={14} className={styles.dropdownIconCreate} />
                  <div className={styles.dropdownContent}>
                    <span className={styles.dropdownName}>
                      Create "{inputValue}"
                    </span>
                    <span className={styles.dropdownHint}>
                      Will be reviewed by admin
                    </span>
                  </div>
                </button>
              )}

              {suggestions.length === 0 && !showCreateOption && (
                <div className={styles.dropdownEmpty}>
                  No skills found
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Helper Text */}
      {!disabled && (
        <div className={styles.helperText}>
          {value.length}/{maxTags} skills • Press Enter to add • New skills require admin approval
        </div>
      )}
    </div>
  );
};

export default TagInput;
