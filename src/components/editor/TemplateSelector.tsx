'use client';

import { useState } from 'react';
import type { TemplateMetadata } from '@/types/template';
import { TEMPLATES } from '@/data/templates';
import { Check } from 'lucide-react';

interface TemplateSelectorProps {
  currentTemplateId: string | null;
  onSelect: (template: TemplateMetadata) => void;
}

export function TemplateSelector({ currentTemplateId, onSelect }: TemplateSelectorProps) {
  const [confirmTemplate, setConfirmTemplate] = useState<TemplateMetadata | null>(null);

  const handleSelect = (template: TemplateMetadata) => {
    if (template.id === currentTemplateId) return;
    setConfirmTemplate(template);
  };

  const handleConfirm = () => {
    if (confirmTemplate) {
      onSelect(confirmTemplate);
      setConfirmTemplate(null);
    }
  };

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2">
        {TEMPLATES.map((template) => {
          const isSelected = template.id === currentTemplateId;
          return (
            <button
              key={template.id}
              onClick={() => handleSelect(template)}
              className={`relative rounded-lg border p-2.5 text-left transition-all ${
                isSelected
                  ? 'border-primary bg-primary/5 ring-1 ring-primary'
                  : 'border-border/50 bg-muted/20 hover:border-border hover:bg-muted/40'
              }`}
            >
              {isSelected && (
                <div className="absolute top-1.5 right-1.5 w-4 h-4 rounded-full bg-primary flex items-center justify-center">
                  <Check className="w-2.5 h-2.5 text-primary-foreground" />
                </div>
              )}
              {/* Thumbnail placeholder */}
              <div className="w-full aspect-square rounded bg-muted/50 border border-border/30 mb-2 flex items-center justify-center">
                <span className="text-2xl">
                  {template.id.includes('cute') ? '🎀' : template.id.includes('slim') ? '✨' : template.id.includes('mature') ? '👤' : '🧑'}
                </span>
              </div>
              <h4 className="text-xs font-medium text-foreground">{template.name}</h4>
              <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2">
                {template.description}
              </p>
            </button>
          );
        })}
      </div>

      {/* Confirmation dialog */}
      {confirmTemplate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card border border-border rounded-lg p-5 mx-4 max-w-sm w-full shadow-xl">
            <h3 className="text-sm font-semibold text-foreground mb-2">템플릿 변경</h3>
            <p className="text-xs text-muted-foreground mb-4">
              <strong>{confirmTemplate.name}</strong> 템플릿으로 변경하시겠습니까?
              <br />
              현재 편집 상태가 초기화됩니다.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setConfirmTemplate(null)}
                className="px-3 py-1.5 text-xs bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleConfirm}
                className="px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
              >
                변경
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
