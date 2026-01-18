import React, { useMemo, useRef, useCallback } from 'react';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
import './RichTextEditor.css';

const DEFAULT_MAX_UPLOAD_MB = 50;

function buildToolbar() {
  return [
    [{ header: [2, 3, false] }],
    ['bold', 'italic', 'underline', 'strike'],
    [{ list: 'ordered' }, { list: 'bullet' }],
    ['blockquote', 'code-block'],
    ['link', 'image', 'attachment'],
    ['clean'],
  ];
}

function getMaxBytes(maxUploadMb) {
  const mb = Number.isFinite(maxUploadMb) ? maxUploadMb : DEFAULT_MAX_UPLOAD_MB;
  return Math.max(1, mb) * 1024 * 1024;
}

export default function RichTextEditor({
  value,
  onChange,
  placeholder = 'Напишите текст…',
  onUploadImage,
  onUploadFile,
  maxUploadMb = DEFAULT_MAX_UPLOAD_MB,
  readOnly = false,
}) {
  const quillRef = useRef(null);

  const pickFile = useCallback((accept) => {
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = accept;
      input.onchange = () => {
        const file = input.files && input.files[0] ? input.files[0] : null;
        resolve(file);
      };
      input.click();
    });
  }, []);

  const insertAtCursor = useCallback((insert) => {
    const quill = quillRef.current?.getEditor?.();
    if (!quill) return;

    const range = quill.getSelection(true);
    const index = range ? range.index : quill.getLength();
    insert(quill, index);
  }, []);

  const handleImage = useCallback(async () => {
    if (!onUploadImage) return;

    const file = await pickFile('image/*');
    if (!file) return;

    const maxBytes = getMaxBytes(maxUploadMb);
    if (file.size > maxBytes) {
      // eslint-disable-next-line no-alert
      alert(`Файл слишком большой. Максимум: ${maxUploadMb} MB`);
      return;
    }

    const result = await onUploadImage(file);
    if (!result?.url) return;

    insertAtCursor((quill, index) => {
      quill.insertEmbed(index, 'image', result.url, 'user');
      quill.setSelection(index + 1, 0, 'user');
    });
  }, [insertAtCursor, maxUploadMb, onUploadImage, pickFile]);

  const handleAttachment = useCallback(async () => {
    if (!onUploadFile) return;

    const file = await pickFile('*/*');
    if (!file) return;

    const maxBytes = getMaxBytes(maxUploadMb);
    if (file.size > maxBytes) {
      // eslint-disable-next-line no-alert
      alert(`Файл слишком большой. Максимум: ${maxUploadMb} MB`);
      return;
    }

    const result = await onUploadFile(file);
    if (!result?.url) return;

    const text = (result.name || file.name || 'Файл').trim();

    insertAtCursor((quill, index) => {
      quill.insertText(index, text, { link: result.url }, 'user');
      quill.insertText(index + text.length, ' ', 'user');
      quill.setSelection(index + text.length + 1, 0, 'user');
    });
  }, [insertAtCursor, maxUploadMb, onUploadFile, pickFile]);

  const modules = useMemo(() => {
    return {
      toolbar: {
        container: buildToolbar(),
        handlers: {
          image: handleImage,
          attachment: handleAttachment,
        },
      },
      clipboard: {
        matchVisual: false,
      },
    };
  }, [handleAttachment, handleImage]);

  const formats = useMemo(
    () => [
      'header',
      'bold',
      'italic',
      'underline',
      'strike',
      'list',
      'bullet',
      'blockquote',
      'code-block',
      'link',
      'image',
    ],
    []
  );

  return (
    <div className={`tp-rich-editor ${readOnly ? 'is-readonly' : ''}`}>
      <ReactQuill
        ref={quillRef}
        theme="snow"
        value={value || ''}
        onChange={onChange}
        placeholder={placeholder}
        modules={modules}
        formats={formats}
        readOnly={readOnly}
      />
    </div>
  );
}
