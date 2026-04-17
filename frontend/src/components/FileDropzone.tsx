import { useRef, useState, type DragEvent } from "react";

export interface FileDropzoneProps {
  onFileSelected: (file: File) => void;
  accept: string;
  maxSizeMb?: number;
}

export function FileDropzone({ onFileSelected, accept, maxSizeMb = 20 }: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [hover, setHover] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = (file: File) => {
    if (accept && !accept.split(",").map((t) => t.trim()).includes(file.type)) {
      setError(`Type de fichier non accepté : ${file.type || "inconnu"}`);
      return;
    }
    if (file.size > maxSizeMb * 1024 * 1024) {
      setError(`Fichier trop volumineux (> ${maxSizeMb} Mo)`);
      return;
    }
    setError(null);
    onFileSelected(file);
  };

  const onDrop = (ev: DragEvent<HTMLDivElement>) => {
    ev.preventDefault();
    setHover(false);
    const file = ev.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div
      data-testid="file-dropzone"
      onDragOver={(e) => { e.preventDefault(); setHover(true); }}
      onDragLeave={() => setHover(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={`rounded-lg border-2 border-dashed p-8 text-center cursor-pointer transition ${
        hover ? "border-primary bg-primary/5" : "border-muted-foreground/30"
      }`}
    >
      <p className="text-sm text-muted-foreground">
        Glisser-déposer un fichier PDF ici, ou cliquer pour parcourir
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Taille maximale : {maxSizeMb} Mo
      </p>
      {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
      />
    </div>
  );
}
