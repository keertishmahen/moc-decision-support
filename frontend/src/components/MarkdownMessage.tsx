/**
 * MarkdownMessage.tsx
 * Lightweight markdown renderer for MoCBot chat responses.
 * Handles: headings, bold, italic, inline code, code blocks,
 * bullet lists, numbered lists, horizontal rules, and tables.
 * No external dependency — pure React.
 */
import React from 'react'

// ── Inline parser — bold, italic, inline code, line breaks ────────────────
function parseInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = []
  // Pattern: **bold**, *italic*, `code`
  const re = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`)/g
  let last = 0
  let m: RegExpExecArray | null

  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index))
    if (m[2] !== undefined) {
      parts.push(<strong key={m.index} className="font-semibold text-white">{m[2]}</strong>)
    } else if (m[3] !== undefined) {
      parts.push(<em key={m.index} className="italic text-white/80">{m[3]}</em>)
    } else if (m[4] !== undefined) {
      parts.push(
        <code key={m.index}
          className="px-1.5 py-0.5 rounded text-[11px] font-mono bg-white/10 text-accent-soft">
          {m[4]}
        </code>
      )
    }
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

// ── Table parser ───────────────────────────────────────────────────────────
function parseTable(lines: string[]): React.ReactNode {
  const rows = lines.map(l =>
    l.replace(/^\||\|$/g, '').split('|').map(c => c.trim())
  )
  const header = rows[0]
  // row[1] is the separator line (---|---) — skip it
  const body = rows.slice(2)

  return (
    <div className="overflow-x-auto my-3">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr>
            {header.map((h, i) => (
              <th key={i}
                className="px-3 py-2 text-left font-semibold text-accent-soft border-b border-white/15 bg-white/[0.04]">
                {parseInline(h)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, ri) => (
            <tr key={ri} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
              {row.map((cell, ci) => (
                <td key={ci} className="px-3 py-1.5 text-white/80 align-top">
                  {parseInline(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Block parser ───────────────────────────────────────────────────────────
type Block =
  | { type: 'h1' | 'h2' | 'h3'; text: string }
  | { type: 'bullet'; items: string[] }
  | { type: 'numbered'; items: string[] }
  | { type: 'code'; lang: string; text: string }
  | { type: 'hr' }
  | { type: 'table'; lines: string[] }
  | { type: 'paragraph'; text: string }

function parseBlocks(markdown: string): Block[] {
  const lines = markdown.split('\n')
  const blocks: Block[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // Fenced code block
    if (line.startsWith('```')) {
      const lang = line.slice(3).trim()
      const codeLines: string[] = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      blocks.push({ type: 'code', lang, text: codeLines.join('\n') })
      i++
      continue
    }

    // Horizontal rule
    if (/^[-*_]{3,}$/.test(line.trim())) {
      blocks.push({ type: 'hr' })
      i++
      continue
    }

    // Headings
    if (line.startsWith('### ')) {
      blocks.push({ type: 'h3', text: line.slice(4) })
      i++; continue
    }
    if (line.startsWith('## ')) {
      blocks.push({ type: 'h2', text: line.slice(3) })
      i++; continue
    }
    if (line.startsWith('# ')) {
      blocks.push({ type: 'h1', text: line.slice(2) })
      i++; continue
    }

    // Table (line starts with | and next line is separator)
    if (line.startsWith('|') && i + 1 < lines.length && /^\|[-| :]+\|/.test(lines[i + 1])) {
      const tableLines: string[] = []
      while (i < lines.length && lines[i].startsWith('|')) {
        tableLines.push(lines[i])
        i++
      }
      blocks.push({ type: 'table', lines: tableLines })
      continue
    }

    // Bullet list
    if (/^[-*•] /.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^[-*•] /.test(lines[i])) {
        items.push(lines[i].replace(/^[-*•] /, ''))
        i++
      }
      blocks.push({ type: 'bullet', items })
      continue
    }

    // Numbered list
    if (/^\d+\. /.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\d+\. /.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\. /, ''))
        i++
      }
      blocks.push({ type: 'numbered', items })
      continue
    }

    // Empty line — skip
    if (line.trim() === '') {
      i++; continue
    }

    // Paragraph — collect consecutive non-special lines
    const paraLines: string[] = []
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].startsWith('#') &&
      !lines[i].startsWith('```') &&
      !/^[-*•] /.test(lines[i]) &&
      !/^\d+\. /.test(lines[i]) &&
      !lines[i].startsWith('|') &&
      !/^[-*_]{3,}$/.test(lines[i].trim())
    ) {
      paraLines.push(lines[i])
      i++
    }
    if (paraLines.length > 0) {
      blocks.push({ type: 'paragraph', text: paraLines.join(' ') })
    }
  }

  return blocks
}

// ── Main component ─────────────────────────────────────────────────────────
interface Props {
  content: string
  className?: string
}

/**
 * Model replies are shown without emojis or pictographic symbols (the interface uses icons).
 * Removes pictographs, dingbats, miscellaneous symbols, keycap/skin-tone/variation modifiers
 * and joiners; arrows and ordinary punctuation are kept because they carry meaning in text.
 */
const EMOJI = /[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{1F1E6}-\u{1F1FF}\u{20E3}\u{FE0E}\u{FE0F}\u{200D}]/gu

export function stripEmoji(text: string): string {
  return text
    .replace(EMOJI, '')
    .replace(/^[ \t]+(?=\S)/gm, m => m)          // keep indentation as is
    .replace(/([^\s]) {2,}/g, '$1 ')             // collapse gaps left inside a line
    .replace(/^(\s*[-*]|\s*\d+\.)\s{2,}/gm, '$1 ') // and after list markers
}

export default function MarkdownMessage({ content, className = '' }: Props) {
  const blocks = parseBlocks(stripEmoji(content ?? ''))

  return (
    <div className={`markdown-body space-y-2 ${className}`}>
      {blocks.map((block, idx) => {
        switch (block.type) {
          case 'h1':
            return (
              <h1 key={idx} className="text-base font-bold text-white mt-3 mb-1 border-b border-white/10 pb-1">
                {parseInline(block.text)}
              </h1>
            )
          case 'h2':
            return (
              <h2 key={idx} className="text-sm font-bold text-accent-soft mt-3 mb-1">
                {parseInline(block.text)}
              </h2>
            )
          case 'h3':
            return (
              <h3 key={idx} className="text-xs font-semibold uppercase tracking-widest text-accent mt-2 mb-1">
                {parseInline(block.text)}
              </h3>
            )

          case 'bullet':
            return (
              <ul key={idx} className="space-y-1 pl-1">
                {block.items.map((item, ii) => (
                  <li key={ii} className="flex items-start gap-2 text-sm text-white/85">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-accent flex-shrink-0" />
                    <span>{parseInline(item)}</span>
                  </li>
                ))}
              </ul>
            )

          case 'numbered':
            return (
              <ol key={idx} className="space-y-1 pl-1">
                {block.items.map((item, ii) => (
                  <li key={ii} className="flex items-start gap-2.5 text-sm text-white/85">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent/20 text-accent text-[10px] font-bold flex items-center justify-center mt-0.5">
                      {ii + 1}
                    </span>
                    <span>{parseInline(item)}</span>
                  </li>
                ))}
              </ol>
            )

          case 'code':
            return (
              <div key={idx} className="rounded-xl overflow-hidden border border-white/10 my-2">
                {block.lang && (
                  <div className="px-3 py-1 bg-white/5 text-[10px] font-mono text-white/40 border-b border-white/8">
                    {block.lang}
                  </div>
                )}
                <pre className="px-4 py-3 text-[11px] font-mono text-accent-soft bg-canvas overflow-x-auto leading-relaxed whitespace-pre-wrap">
                  {block.text}
                </pre>
              </div>
            )

          case 'hr':
            return <hr key={idx} className="border-white/10 my-2" />

          case 'table':
            return <div key={idx}>{parseTable(block.lines)}</div>

          case 'paragraph':
            return (
              <p key={idx} className="text-sm text-white/85 leading-relaxed">
                {parseInline(block.text)}
              </p>
            )

          default:
            return null
        }
      })}
    </div>
  )
}
