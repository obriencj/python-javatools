;; cheetah-mode.el
;;
;; original from http://www.emacswiki.org/emacs/CheetahMode
;;
;; updated by obriencj@gmail.com to understand block, elif, implements.
;;
;; wishlist: make PSP <% %> sections look like python-mode

(define-derived-mode cheetah-mode html-mode "Cheetah"
  (make-face 'cheetah-variable-face)
  (font-lock-add-keywords
   nil
   '(("\\(#\\(from\\|else\\|include\\|extends\\|implements\\|block\\|set\\|def\\|import\\|for\\|if\\|elif\\|end\\)+\\)\\>" 1 font-lock-type-face)
     ("\\(#\\(from\\|for\\|end\\)\\).*\\<\\(for\\|import\\|block\\|def\\|if\\|in\\)\\>" 3 font-lock-type-face)
     ("\\(##.*\\)\n" 1 font-lock-comment-face)
     ("\\(\\$\\(?:\\sw\\|}\\|{\\|\\s_\\)+\\)" 1 font-lock-variable-name-face)))
  (font-lock-mode 1))

(provide 'cheetah-mode)
(add-to-list 'auto-mode-alist '("\\.tmpl$" . cheetah-mode))
