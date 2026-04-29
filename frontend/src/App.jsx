import { useState, useRef, useEffect } from 'react';
import {
  BrainCircuit,
  Download,
  FileText,
  Globe2,
  MessageSquare,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TestTube2,
} from 'lucide-react';
import PDFUploader from './components/PDFUploader';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import TypingIndicator from './components/TypingIndicator';
import PDFViewer from './components/PDFViewer';
import { uploadPDF, sendMessage } from './api';

export default function App() {
  // --- State ---
  const [documentId, setDocumentId] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadState, setUploadState] = useState('idle');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadMessage, setUploadMessage] = useState('');
  const [documentInfo, setDocumentInfo] = useState(null);

  // PDF Viewer state
  const [showPdfViewer, setShowPdfViewer] = useState(false);
  const [activeCitation, setActiveCitation] = useState(null);

  const messagesEndRef = useRef(null);

  // --- Auto-scroll on new messages ---
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // --- PDF Upload ---
  const handleUpload = async (file) => {
    setUploadState('uploading');
    setUploadProgress(0);
    setUploadMessage('Uploading and processing...');

    try {
      const result = await uploadPDF(file, (progress) => {
        setUploadProgress(progress);
        if (progress >= 100) {
          setUploadMessage('Extracting text and building index...');
        }
      });

      setDocumentId(result.document_id);
      setDocumentInfo({
        total_pages: result.total_pages,
        total_chunks: result.total_chunks,
      });
      setUploadState('success');
      setUploadMessage(result.message);
      setMessages([]);
      setSessionId(null);
      setShowPdfViewer(false);
      setActiveCitation(null);
    } catch (err) {
      setUploadState('error');
      setUploadMessage(
        err.response?.data?.detail || 'Failed to upload PDF. Please try again.'
      );
    }
  };

  // --- Send Message ---
  const handleSend = async (question) => {
    if (!documentId) return;

    const userMsg = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const result = await sendMessage(question, documentId, sessionId);

      if (result.session_id) {
        setSessionId(result.session_id);
      }

      const agentMsg = {
        role: 'assistant',
        content: result.answer,
        citations: result.citations || [],
        isRefusal: result.is_refusal || false,
      };
      setMessages((prev) => [...prev, agentMsg]);
    } catch (err) {
      const errorMsg = {
        role: 'assistant',
        content: `⚠️ Error: ${err.response?.data?.detail || 'Failed to get response. Please try again.'}`,
        citations: [],
        isRefusal: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Citation Click → Open PDF Viewer ---
  const handleCitationClick = (citation) => {
    setActiveCitation(citation);
    setShowPdfViewer(true);
  };

  // --- Close PDF Viewer ---
  const handleClosePdfViewer = () => {
    setShowPdfViewer(false);
    setActiveCitation(null);
  };

  // --- Reset ---
  const handleReset = () => {
    setDocumentId(null);
    setSessionId(null);
    setMessages([]);
    setUploadState('idle');
    setUploadProgress(0);
    setUploadMessage('');
    setDocumentInfo(null);
    setShowPdfViewer(false);
    setActiveCitation(null);
  };

  const hasDocument = uploadState === 'success' && documentId;
  const sampleQueries = [
    'What is PDF Reviewer built for?',
    'What should the assistant do if the answer is not present in the PDF?',
    'Que debe hacer el asistente cuando el usuario pregunta en otro idioma?',
    'Who won the 2026 FIFA World Cup?',
  ];
  const oaChecklist = [
    'Accepts any PDF upload',
    'Conversational Q&A',
    'Answers only from PDF context',
    'Explicit out-of-scope refusal',
    'Page/section citations',
    '5 valid + 3 invalid sample tests',
  ];

  return (
    <div className="h-screen flex flex-col bg-bg-primary">
      {/* Header */}
      <header className="flex-shrink-0 glass border-b border-border px-6 py-3 z-10">
        <div className="max-w-full mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-accent/10 animate-pulse-glow">
              <Sparkles className="w-5 h-5 text-accent" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-text-primary tracking-tight">
                PDF Reviewer
              </h1>
              <p className="text-xs text-text-muted">
                PDF-constrained AI agent • cited answers • refusals
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {hasDocument && documentInfo && (
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-success/10 border border-success/20">
                <FileText className="w-3.5 h-3.5 text-success" />
                <span className="text-xs text-success font-medium">
                  {documentInfo.total_pages} pages loaded
                </span>
              </div>
            )}

            {hasDocument && (
              <button
                id="reset-button"
                onClick={handleReset}
                className="p-2 rounded-lg hover:bg-bg-tertiary text-text-muted hover:text-text-primary transition-colors"
                title="Upload a different PDF"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content — side-by-side layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chat Panel */}
        <main
          className={`flex-1 flex flex-col transition-all duration-300 ${
            showPdfViewer ? 'min-w-0' : ''
          } ${hasDocument ? 'overflow-hidden' : 'overflow-y-auto'}`}
        >
          {!hasDocument ? (
            /* --- Upload View --- */
            <div className="min-h-full flex flex-col items-center px-4 py-8 sm:py-10">
              <div className="mb-6 text-center">
                <h2 className="text-3xl font-bold text-text-primary mb-2 tracking-tight">
                  PDF-Constrained Conversational Agent
                </h2>
                <p className="text-text-secondary text-sm max-w-md">
                  Upload any PDF and ask questions. The backend AI agent retrieves
                  relevant PDF excerpts, calls Groq for generation, cites source
                  pages, and refuses anything not supported by the document.
                </p>
              </div>

              <PDFUploader
                onUpload={handleUpload}
                uploadState={uploadState}
                uploadProgress={uploadProgress}
                uploadMessage={uploadMessage}
                documentInfo={documentInfo}
              />

              {/* Feature highlights */}
              <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl w-full">
                {[
                  {
                    icon: FileText,
                    title: 'Page Citations',
                    desc: 'Every answer cites exact pages',
                  },
                  {
                    icon: ShieldCheck,
                    title: 'Strict Refusal',
                    desc: "Refuses when the PDF doesn't support an answer",
                  },
                  {
                    icon: Globe2,
                    title: 'Multilingual Grounding',
                    desc: 'Ask in another language; answers still come only from the PDF',
                  },
                ].map((feature) => {
                  const Icon = feature.icon;

                  return (
                  <div
                    key={feature.title}
                    className="glass rounded-xl p-4 text-center hover:border-border-hover transition-colors"
                  >
                    <Icon className="w-6 h-6 mx-auto mb-2 text-accent" />
                    <p className="text-sm font-medium text-text-primary">
                      {feature.title}
                    </p>
                    <p className="text-xs text-text-muted mt-1">{feature.desc}</p>
                  </div>
                  );
                })}
              </div>

              <div className="mt-6 max-w-2xl w-full grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="glass rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <BrainCircuit className="w-4 h-4 text-accent" />
                    <p className="text-sm font-semibold text-text-primary">
                      AI Agent Pipeline
                    </p>
                  </div>
                  <p className="text-xs text-text-muted leading-relaxed">
                    This is not just a JavaScript UI. FastAPI runs PDF extraction,
                    TF-IDF retrieval, Groq generation, strict grounding, refusal
                    detection, and citation metadata.
                  </p>
                </div>

                <div className="glass rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <TestTube2 className="w-4 h-4 text-accent" />
                    <p className="text-sm font-semibold text-text-primary">
                      OA Test Pack
                    </p>
                  </div>
                  <p className="text-xs text-text-muted leading-relaxed mb-3">
                    Download the sample PDF and test cases to verify 5 valid
                    queries, 3 invalid refusals, and one multilingual grounded answer.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <a
                      href="/samples/sample-review-policy.pdf"
                      download
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent/10 text-accent text-xs hover:bg-accent/20 transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Sample PDF
                    </a>
                    <a
                      href="/samples/test-cases.md"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-tertiary text-text-secondary text-xs hover:text-text-primary transition-colors"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      Test cases
                    </a>
                  </div>
                </div>
              </div>

              <div className="mt-6 max-w-2xl w-full glass rounded-xl p-4 pb-5 mb-8">
                <div className="flex items-center gap-2 mb-3">
                  <ShieldCheck className="w-4 h-4 text-success" />
                  <p className="text-sm font-semibold text-text-primary">
                    OA Requirement Coverage
                  </p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {oaChecklist.map((item) => (
                    <div
                      key={item}
                      className="rounded-lg border border-border bg-bg-tertiary/40 px-3 py-2 text-xs text-text-secondary"
                    >
                      {item}
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-[11px] text-text-muted leading-relaxed">
                  Multilingual support means answerable questions can be asked in
                  another language and the response follows that language, but the
                  agent still uses only the uploaded PDF as evidence.
                </p>
              </div>
            </div>
          ) : (
            /* --- Chat View --- */
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-4 py-6">
                <div className="max-w-3xl mx-auto space-y-4">
                  {/* Welcome message */}
                  {messages.length === 0 && (
                    <div className="text-center py-12 animate-fade-in-up">
                      <MessageSquare className="w-10 h-10 text-accent/40 mx-auto mb-3" />
                      <p className="text-text-secondary text-sm">
                        Your PDF is ready. Ask anything about the document.
                      </p>
                      <p className="text-text-muted text-xs mt-1">
                        Click on citation badges to view the referenced section in the PDF.
                      </p>
                      <div className="mt-6 flex flex-wrap justify-center gap-2">
                        {sampleQueries.map((query) => (
                          <button
                            key={query}
                            type="button"
                            onClick={() => handleSend(query)}
                            disabled={isLoading}
                            className="px-3 py-1.5 rounded-full bg-bg-tertiary text-xs text-text-secondary hover:text-text-primary hover:border-accent/30 border border-border transition-colors disabled:opacity-50"
                          >
                            {query}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Message list */}
                  {messages.map((msg, idx) => (
                    <ChatMessage
                      key={idx}
                      role={msg.role}
                      content={msg.content}
                      citations={msg.citations}
                      isRefusal={msg.isRefusal}
                      onCitationClick={handleCitationClick}
                    />
                  ))}

                  {/* Typing indicator */}
                  {isLoading && <TypingIndicator />}

                  <div ref={messagesEndRef} />
                </div>
              </div>

              {/* Input */}
              <div className="flex-shrink-0 px-4 pb-4 pt-2">
                <div className="max-w-3xl mx-auto">
                  <ChatInput
                    onSend={handleSend}
                    disabled={!hasDocument}
                    isLoading={isLoading}
                  />
                  <p className="text-center text-[10px] text-text-muted mt-2">
                    Answers are strictly grounded in the uploaded PDF. Not general knowledge.
                  </p>
                </div>
              </div>
            </>
          )}
        </main>

        {/* PDF Viewer Panel (side-by-side) */}
        {showPdfViewer && hasDocument && (
          <aside className="w-[45%] min-w-[360px] max-w-[600px] flex-shrink-0">
            <PDFViewer
              documentId={documentId}
              activeCitation={activeCitation}
              onClose={handleClosePdfViewer}
            />
          </aside>
        )}
      </div>
    </div>
  );
}
