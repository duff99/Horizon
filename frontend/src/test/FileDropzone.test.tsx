import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { FileDropzone } from "../components/FileDropzone";

describe("FileDropzone", () => {
  it("displays French instructions", () => {
    render(<FileDropzone onFileSelected={() => {}} accept="application/pdf" />);
    expect(screen.getByText(/glisser/i)).toBeInTheDocument();
  });

  it("calls onFileSelected when file is dropped", () => {
    const handler = vi.fn();
    render(<FileDropzone onFileSelected={handler} accept="application/pdf" />);
    const zone = screen.getByTestId("file-dropzone");
    const file = new File([new Uint8Array([1])], "x.pdf", { type: "application/pdf" });
    fireEvent.drop(zone, { dataTransfer: { files: [file] } });
    expect(handler).toHaveBeenCalledWith(file);
  });

  it("rejects files with wrong mime", () => {
    const handler = vi.fn();
    render(<FileDropzone onFileSelected={handler} accept="application/pdf" />);
    const zone = screen.getByTestId("file-dropzone");
    const file = new File([new Uint8Array([1])], "x.txt", { type: "text/plain" });
    fireEvent.drop(zone, { dataTransfer: { files: [file] } });
    expect(handler).not.toHaveBeenCalled();
  });
});
