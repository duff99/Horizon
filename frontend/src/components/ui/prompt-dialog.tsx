/**
 * PromptDialog — équivalent stylé de `window.prompt`, basé sur `Modal`.
 *
 * Remplace les `window.prompt` natifs (UI navigateur grise, position
 * imprévisible, hors charte). Le composant gère son propre état d'input
 * et soumet via Enter ou clic.
 */
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";

interface PromptDialogProps {
  open: boolean;
  title: string;
  description?: React.ReactNode;
  label: string;
  placeholder?: string;
  initialValue?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  busy?: boolean;
  /** Validation locale. Retourne un message d'erreur ou null si OK. */
  validate?: (value: string) => string | null;
  onConfirm: (value: string) => void;
  onCancel: () => void;
}

export function PromptDialog({
  open,
  title,
  description,
  label,
  placeholder,
  initialValue = "",
  confirmLabel = "Valider",
  cancelLabel = "Annuler",
  busy = false,
  validate,
  onConfirm,
  onCancel,
}: PromptDialogProps) {
  const [value, setValue] = useState(initialValue);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setValue(initialValue);
      setError(null);
      const t = setTimeout(() => inputRef.current?.focus(), 0);
      return () => clearTimeout(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function handleConfirm() {
    const trimmed = value.trim();
    if (!trimmed) {
      setError("Ce champ est obligatoire.");
      return;
    }
    if (validate) {
      const msg = validate(trimmed);
      if (msg) {
        setError(msg);
        return;
      }
    }
    onConfirm(trimmed);
  }

  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      description={description}
      size="md"
      busy={busy}
      footer={
        <>
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            disabled={busy}
            className="h-8"
          >
            {cancelLabel}
          </Button>
          <Button
            type="button"
            onClick={handleConfirm}
            disabled={busy}
            className="h-8"
          >
            {busy ? "…" : confirmLabel}
          </Button>
        </>
      }
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleConfirm();
        }}
        className="space-y-2"
      >
        <label
          htmlFor="prompt-input"
          className="block text-[12.5px] font-medium text-ink-2"
        >
          {label}
        </label>
        <Input
          id="prompt-input"
          ref={inputRef}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            if (error) setError(null);
          }}
          placeholder={placeholder}
          disabled={busy}
        />
        {error && (
          <p role="alert" className="text-[11.5px] text-rose-700">
            {error}
          </p>
        )}
      </form>
    </Modal>
  );
}
