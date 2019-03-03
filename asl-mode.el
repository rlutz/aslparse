;;; asl-mode.el --- Major mode for editing ASL files

;; Copyright (C) 2019 Roland Lutz

;; Author: Roland Lutz
;; Keywords: languages

;; This file is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published by
;; the Free Software Foundation; either version 2, or (at your option)
;; any later version.

;; This file is distributed in the hope that it will be useful,
;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;; GNU General Public License for more details.

;; You should have received a copy of the GNU General Public License
;; along with this file.  If not, see <https://www.gnu.org/licenses/>.

;;; Commentary:

;; A major mode for editing ASL files.  It provides basic syntax
;; highlighting and indentation.

;; The indentation commands (C-c <, C-c >) are copied from python.el.

;;; Code:

(defvar asl-mode-hook nil)

(defvar asl-mode-map
  (let ((map (make-sparse-keymap)))
    (define-key map "\C-c<" 'asl-indent-shift-left)
    (define-key map "\C-c>" 'asl-indent-shift-right)
    (easy-menu-define asl-menu map "ASL Mode menu"
      `("ASL"
        :help "ASL-specific Features"
        ["Shift region left" asl-indent-shift-left :active mark-active
         :help "Shift region left by a single indentation step"]
        ["Shift region right" asl-indent-shift-right :active mark-active
         :help "Shift region right by a single indentation step"]))
    map)
  "Keymap for ASL mode.")

(defvar asl-mode-syntax-table
  (let ((st (make-syntax-table)))
    (modify-syntax-entry ?/ ". 124b" st)
    (modify-syntax-entry ?* ". 23" st)
    (modify-syntax-entry ?\n "> b" st)
    st)
  "Syntax table for ASL mode.")

(defvar asl-keywords
  '("AND" "DIV" "EOR" "IMPLEMENTATION_DEFINED" "IN" "MOD" "NOT" "OR" "REM"
    "SEE" "UNDEFINED" "UNKNOWN" "UNPREDICTABLE"
    "array" "assert" "case" "constant" "do" "downto" "else" "elsif"
    "enumeration" "for" "if" "is" "of" "otherwise" "repeat" "return" "then"
    "to" "until" "when" "while"))

(defvar asl-builtins
  '("type"))

(defvar asl-types
  '("bit" "bits" "boolean" "integer"))

(defvar asl-constants
  '("TRUE" "FALSE" "HIGH" "LOW"))

(defface asl-bitvector-face
  '((t (:foreground "#804000")))
  "red")

(defvar asl-font-lock-defaults
  `(((,(regexp-opt asl-keywords 'symbols) . font-lock-keyword-face)
     (,(regexp-opt asl-builtins 'symbols) . font-lock-builtin-face)
     (,(regexp-opt asl-types 'symbols) . font-lock-type-face)
     (,(regexp-opt asl-constants 'symbols) . font-lock-constant-face)
     ("#\\|\\$\\|%\\|\\?\\|@\\|\\\\\\|`\\|~\\|[^\n -~]"
        . font-lock-warning-face)
     ("\\('[01x ]*'\\)" . 'asl-bitvector-face))))

(defvar asl-indent-offset 4)

(defun asl-indent-line-function ()
  "Indent current line of ASL code."
  (interactive)
  (let* ((indent
	  (if (and (eq last-command this-command)
		   (> (current-indentation) 0))
	      (* (/ (- (current-indentation) 1) asl-indent-offset)
		 asl-indent-offset)
	    (asl-calculate-indentation)))
	 (savep (> (current-column) (current-indentation))))
    (if savep
	(save-excursion (indent-line-to indent))
      (indent-line-to indent))))

(defun asl-backward-source-line ()
  "Move back to the last source (non-empty and non-comment) line."
  (forward-line -1)
  (while (and (not (bobp))
	      (looking-at "^[\t ]*\\(//[^\n]*\\)?$"))
    (forward-line -1)))

(defun asl-calculate-indentation ()
  "Return the column to which the current line should be indented."
  (if (save-excursion (beginning-of-line) (bobp))
      0
    (let ((prev-indentation
	   (save-excursion
	     (asl-backward-source-line)
	     (current-indentation)))
	  (prev-starts-block
	   (save-excursion
	     (asl-backward-source-line)
	     (looking-at "^[^\n]*[^\n\t ;][\t ]*\\(//[^\n]*\\)?$"))))
      (if prev-starts-block
	  (+ prev-indentation asl-indent-offset)
	prev-indentation))))

;;;###autoload
(define-derived-mode asl-mode fundamental-mode "ASL"
  "Major mode for editing ASL files."
  :syntax-table asl-mode-syntax-table
  (setq-local comment-start "// ")
  (setq-local comment-start-skip "\\(//+\\|/\\*+\\)\\s *")
  (setq-local comment-end-skip nil)
  (setq-local font-lock-defaults asl-font-lock-defaults)
  (setq-local indent-line-function 'asl-indent-line-function))


;;; Indentation commands (copied from python.el)

(defun asl-indent-shift-right (start end &optional count)
  "Shift lines contained in region START END by COUNT columns to the right.
COUNT defaults to `asl-indent-offset'.  If region isn't active,
the current line is shifted.  The shifted region includes the
lines in which START and END lie."
  (interactive
   (if mark-active
       (list (region-beginning) (region-end) current-prefix-arg)
     (list (line-beginning-position) (line-end-position) current-prefix-arg)))
  (let ((deactivate-mark nil))
    (setq count (if count (prefix-numeric-value count)
                  asl-indent-offset))
    (indent-rigidly start end count)))

(defun asl-indent-shift-left (start end &optional count)
  "Shift lines contained in region START END by COUNT columns to the left.
COUNT defaults to `asl-indent-offset'.  If region isn't active,
the current line is shifted.  The shifted region includes the
lines in which START and END lie.  An error is signaled if any
lines in the region are indented less than COUNT columns."
  (interactive
   (if mark-active
       (list (region-beginning) (region-end) current-prefix-arg)
     (list (line-beginning-position) (line-end-position) current-prefix-arg)))
  (if count
      (setq count (prefix-numeric-value count))
    (setq count asl-indent-offset))
  (when (> count 0)
    (let ((deactivate-mark nil))
      (save-excursion
        (goto-char start)
        (while (< (point) end)
          (if (and (< (current-indentation) count)
                   (not (looking-at "[ \t]*$")))
              (error "Can't shift all lines enough"))
          (forward-line))
        (indent-rigidly start end (- count))))))


(provide 'asl-mode)

;;; asl-mode.el ends here
