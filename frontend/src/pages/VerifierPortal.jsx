import { useState } from 'react'
import FileDropzone from '../components/FileDropzone.jsx'
import ProcessFlow from '../components/ProcessFlow.jsx'
import SampleOutputs from '../components/SampleOutputs.jsx'
import { api } from '../services/api.js'
import { addActivity } from '../utils/activity.js'

export default function VerifierPortal() {
    const [file, setFile] = useState(null)
    const [rollNumber, setRollNumber] = useState('')
    const [ocrLoading, setOcrLoading] = useState(false)
    const [verifying, setVerifying] = useState(false)
    const [result, setResult] = useState(null)
    const [ocrData, setOcrData] = useState(null)
    const [error, setError] = useState('')

    // Calculate current step for ProcessFlow
    const getCurrentStep = () => {
        if (!file) return 0
        if (ocrLoading) return 1
        if (verifying) return 3
        return result ? 4 : 2
    }

    const currentStep = getCurrentStep()

    async function handleSampleSelect(sample) {
        setRollNumber(sample.rollNumber)
        setOcrData({
            raw_text: `Student Name: ${sample.studentName}\nRoll Number: ${sample.rollNumber}\nDegree: ${sample.degree}\nUniversity: ${sample.universityName}`,
            confidence: 'high',
            is_academic: true,
            category: 'University Degree Certificate',
            student_name: sample.studentName,
            university_name: sample.universityName,
            degree: sample.degree,
            roll_number: sample.rollNumber,
        })
        setResult(null)
        setError('')
        addActivity({
            type: 'sample-used',
            title: 'Sample certificate loaded for verification',
            detail: `Pre-filled data for ${sample.studentName}`,
            actorRole: 'verifier',
        })
        if (window.addToast) {
            window.addToast(`Sample loaded: ${sample.studentName}`, 'info', 3000)
        }
    }

    async function handleFile(f) {
        setFile(f)
        setResult(null)
        setError('')
        setOcrData(null)
        setOcrLoading(true)

        try {
            const res = await api.ocrFile(f)
            setOcrData(res)

            if (res.roll_number) {
                setRollNumber(res.roll_number)
            } else if (!res.is_academic) {
                setRollNumber('')
            }

            if (!res.is_academic && window.addToast) {
                window.addToast(`Warning: File identified as ${res.category}, not an academic degree.`, 'error', 5000)
            }
        } catch (err) {
            console.error('OCR processing error:', err)
            setError('Failed to extract text from file. Please ensure the backend is running.')
        } finally {
            setOcrLoading(false)
        }
    }

    async function handleVerify() {
        if (!file) return
        setVerifying(true)
        setResult(null)
        setError('')

        try {
            const res = await api.verifyCertificate(file, rollNumber)
            setResult(res)

            let actTitle = ''
            let actDetail = ''
            let actType = 'verify-failed'

            if (!res.is_academic) {
                actTitle = `Rejected Non-Academic Document (${res.category})`
                actDetail = `Uploaded file does not match degree or marksheet structure.`
            } else if (res.verified) {
                actType = 'verify-success'
                actTitle = `Verification passed: ${res.roll_number || 'Valid Credential'}`
                actDetail = `Authenticated: ${res.student_name || 'Academic Holder'} (${res.university_name || 'Recognized University'})`
            } else {
                actTitle = `Verification flagged/failed for ${res.roll_number || 'Document'}`
                actDetail = res.verdict?.includes('TAMPERED')
                    ? 'Hash mismatch with registered blockchain mint.'
                    : res.message
            }

            addActivity({
                type: actType,
                title: actTitle,
                detail: actDetail,
                actorRole: 'verifier',
            })
        } catch (e) {
            console.error('Verification error:', e)
            setError(e?.response?.data?.detail || 'Verification service error. Please check backend connection.')
        } finally {
            setVerifying(false)
        }
    }

    return (
        <div className="page-content fade-in">
            <div className="page-header">
                <h2>Verify University Degree & Marksheet</h2>
                <p>Upload official degrees, diplomas, or transcripts of any university. Multi-vector audit verifies real credentials and flags fake or absurd documents.</p>
            </div>

            {/* Process Flow */}
            <ProcessFlow type="verifier" currentStep={currentStep} />

            {/* Document Type Warning Banner if non-academic file is detected */}
            {ocrData && !ocrData.is_academic && (
                <div className="alert alert-danger" style={{ background: 'rgba(239, 68, 68, 0.12)', border: '1px solid var(--red-600)', color: 'var(--red-600)', marginBottom: 20 }}>
                    <span style={{ fontSize: 20 }}>⚠️</span>
                    <div>
                        <strong>Non-Academic Document Detected ({ocrData.category}):</strong> This file does not appear to be an official university degree certificate or marksheet.
                    </div>
                </div>
            )}

            <div className="grid-3" style={{ gap: 24, alignItems: 'start' }}>
                {/* Left Column: Upload & OCR Inspection */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                    <div className="card">
                        <div className="card-header">
                            <div>
                                <div className="card-title">📎 Upload Document</div>
                                <div className="card-subtitle">PDF, PNG, JPG, or Scanned Marksheet</div>
                            </div>
                        </div>
                        <div className="card-body">
                            <FileDropzone onFile={handleFile} label="Drop university degree or marksheet here" />

                            {ocrLoading && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 16, color: 'var(--gray-500)' }}>
                                    <div className="spinner" style={{ borderTopColor: 'var(--orange-500)', borderColor: 'var(--gray-200)' }} />
                                    Analyzing document structure & OCR text…
                                </div>
                            )}

                            {ocrData && (
                                <div style={{ marginTop: 16 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                                        <div className="form-label" style={{ margin: 0 }}>
                                            Document Analysis
                                        </div>
                                        <span className={`pill ${ocrData.is_academic ? 'pill-green' : 'pill-red'}`} style={{ fontSize: 11 }}>
                                            {ocrData.category || (ocrData.is_academic ? 'Academic Credential' : 'Non-Academic')}
                                        </span>
                                    </div>

                                    {/* Extracted Entity Summary */}
                                    {ocrData.is_academic && (
                                        <div style={{ background: 'var(--gray-50)', padding: '10px 12px', borderRadius: 'var(--radius-md)', fontSize: 12, marginBottom: 10, border: '1px solid var(--gray-200)' }}>
                                            {ocrData.university_name && (
                                                <div style={{ marginBottom: 4 }}>
                                                    <strong>🏛️ University:</strong> {ocrData.university_name}
                                                </div>
                                            )}
                                            {ocrData.student_name && (
                                                <div style={{ marginBottom: 4 }}>
                                                    <strong>👤 Student:</strong> {ocrData.student_name}
                                                </div>
                                            )}
                                            {ocrData.degree && (
                                                <div style={{ marginBottom: 4 }}>
                                                    <strong>📜 Program:</strong> {ocrData.degree}
                                                </div>
                                            )}
                                            {ocrData.roll_number && (
                                                <div>
                                                    <strong>🔑 Roll No:</strong> {ocrData.roll_number}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    <div style={{
                                        background: 'var(--gray-900)', color: 'var(--orange-300)', fontFamily: 'monospace',
                                        fontSize: 11, padding: '12px 14px', borderRadius: 'var(--radius-md)', lineHeight: 1.6,
                                        maxHeight: 120, overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all'
                                    }}>
                                        {ocrData.raw_text || 'No text extracted.'}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="card">
                        <div className="card-header">
                            <div>
                                <div className="card-title">🔑 Roll / Registration Number</div>
                                <div className="card-subtitle">Auto-detected from document, or enter manually</div>
                            </div>
                        </div>
                        <div className="card-body">
                            <div className="form-group" style={{ marginBottom: 0 }}>
                                <input
                                    className="form-input"
                                    placeholder="e.g. 2411200010023 or BTH20200123"
                                    value={rollNumber}
                                    onChange={e => setRollNumber(e.target.value)}
                                />
                                <div className="form-hint">
                                    {rollNumber ? `✓ Roll number: ${rollNumber}` : 'Will be automatically populated from degree or marksheet'}
                                </div>
                            </div>
                        </div>
                    </div>

                    <button
                        className="btn btn-primary btn-lg"
                        onClick={handleVerify}
                        disabled={!file || verifying || ocrLoading}
                        style={{ width: '100%' }}
                    >
                        {verifying
                            ? <><div className="spinner" /> Auditing Authenticity…</>
                            : '🛡️  Verify Authenticity Now'}
                    </button>
                </div>

                {/* Middle Column: Verification Results */}
                <div>
                    {!result && !error && (
                        <div className="card" style={{ textAlign: 'center', padding: '60px 32px' }}>
                            <div style={{ fontSize: 56, marginBottom: 16 }}>🔍</div>
                            <div style={{ fontSize: 17, fontWeight: 700, color: 'var(--gray-700)' }}>Ready for Verification</div>
                            <div style={{ fontSize: 14, color: 'var(--gray-400)', marginTop: 8, lineHeight: 1.6 }}>
                                Upload any university degree or marksheet to perform forensic analysis, verify against blockchain, and detect fake or non-academic files.
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="result-panel failed fade-in">
                            <div className="result-icon err">⚠️</div>
                            <div className="result-title err">Verification Error</div>
                            <div className="result-message">{error}</div>
                        </div>
                    )}

                    {/* Result Case 1: NOT A DEGREE OR MARKSHEET (REJECTED) */}
                    {result && !result.is_academic && (
                        <div className="result-panel failed fade-in" style={{ borderColor: 'var(--red-600)', background: 'rgba(239, 68, 68, 0.04)' }}>
                            <div className="result-icon err">⚠️</div>
                            <div className="result-title err" style={{ color: 'var(--red-600)' }}>
                                REJECTED — NOT A DEGREE OR MARKSHEET
                            </div>
                            <div style={{ display: 'inline-block', margin: '8px 0 12px', padding: '4px 12px', borderRadius: 20, background: 'rgba(239, 68, 68, 0.15)', color: 'var(--red-600)', fontWeight: 700, fontSize: 12 }}>
                                Detected: {result.category}
                            </div>
                            <div className="result-message" style={{ fontSize: 14, lineHeight: 1.6 }}>
                                {result.message}
                            </div>

                            {/* Rejection Reasons */}
                            {result.risk_flags && result.risk_flags.length > 0 && (
                                <div style={{ marginTop: 20, textAlign: 'left', background: '#fff', padding: 16, borderRadius: 'var(--radius-md)', border: '1px solid var(--gray-200)' }}>
                                    <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--gray-800)', marginBottom: 8 }}>
                                        Why this document was rejected:
                                    </div>
                                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: 'var(--gray-600)', lineHeight: 1.6 }}>
                                        {result.risk_flags.map((r, i) => (
                                            <li key={i} style={{ marginBottom: 4 }}>{r}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            <div style={{ marginTop: 20, padding: 12, background: 'var(--orange-50)', border: '1px dashed var(--orange-300)', borderRadius: 'var(--radius-md)', fontSize: 12, color: 'var(--orange-900)' }}>
                                💡 <strong>Action Required:</strong> {result.recommendation || 'Please upload an official university degree certificate, diploma, or marksheet/transcript.'}
                            </div>
                        </div>
                    )}

                    {/* Result Case 2: ACADEMIC CREDENTIAL (REAL or FAKE / TAMPERED) */}
                    {result && result.is_academic && (
                        <div className={`result-panel ${result.verified ? 'verified' : 'failed'} fade-in`}>
                            <div className={`result-icon ${result.verified ? 'ok' : 'err'}`}>
                                {result.verified ? '✅' : '❌'}
                            </div>
                            <div className={`result-title ${result.verified ? 'ok' : 'err'}`}>
                                {result.verdict}
                            </div>

                            {/* Authenticity Score Gauge */}
                            <div style={{ margin: '12px auto', maxWidth: 280, textAlign: 'center' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, fontWeight: 700, marginBottom: 4, color: result.verified ? 'var(--green-700)' : 'var(--red-700)' }}>
                                    <span>Authenticity Rating</span>
                                    <span>{result.authenticity_score}%</span>
                                </div>
                                <div style={{ height: 8, background: 'var(--gray-200)', borderRadius: 4, overflow: 'hidden' }}>
                                    <div style={{
                                        height: '100%',
                                        width: `${result.authenticity_score}%`,
                                        background: result.authenticity_score >= 70 ? 'var(--green-600)' : result.authenticity_score >= 45 ? 'var(--orange-500)' : 'var(--red-600)',
                                        transition: 'width 0.8s ease'
                                    }} />
                                </div>
                            </div>

                            <div className="result-message" style={{ marginTop: 12, fontSize: 14 }}>
                                {result.message}
                            </div>

                            {/* Extracted Details */}
                            <div className="cert-details" style={{ marginTop: 20 }}>
                                {[
                                    { k: 'Document Category', v: result.category },
                                    { k: 'Roll / Reg Number', v: result.roll_number },
                                    { k: 'Student Name', v: result.student_name },
                                    { k: 'University / Board', v: result.university_name },
                                    { k: 'Degree / Program', v: result.degree },
                                    { k: 'Date of Issue', v: result.issued_at },
                                    { k: 'File Fingerprint (SHA-256)', v: result.submitted_hash, mono: true },
                                    { k: 'Blockchain Authority', v: result.issued_by, mono: true },
                                ].filter(r => r.v && r.v !== 'N/A').map(r => (
                                    <div key={r.k} className="cert-details-row">
                                        <span className="cert-details-key">{r.k}</span>
                                        <span className="cert-details-val" style={r.mono ? { fontSize: 11, fontFamily: 'monospace', wordBreak: 'break-all' } : {}}>{r.v}</span>
                                    </div>
                                ))}
                            </div>

                            {/* Multi-Factor Audit Checklist */}
                            {result.audit_checks && result.audit_checks.length > 0 && (
                                <div style={{ marginTop: 20, textAlign: 'left', background: '#fff', padding: 16, borderRadius: 'var(--radius-md)', border: '1px solid var(--gray-200)' }}>
                                    <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--gray-800)', marginBottom: 12 }}>
                                        🛡️ Multi-Vector Forensic Audit:
                                    </div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                        {result.audit_checks.map((chk, i) => (
                                            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 12 }}>
                                                <span style={{ fontSize: 14 }}>
                                                    {chk.status === 'passed' ? '✅' : chk.status === 'warning' ? '⚠️' : chk.status === 'failed' ? '❌' : 'ℹ️'}
                                                </span>
                                                <div>
                                                    <strong style={{ color: 'var(--gray-800)' }}>{chk.name}: </strong>
                                                    <span style={{ color: 'var(--gray-600)' }}>{chk.detail}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Risk Flags if Tampered or Fake */}
                            {result.risk_flags && result.risk_flags.length > 0 && (
                                <div style={{ marginTop: 16, textAlign: 'left', background: 'rgba(239, 68, 68, 0.08)', padding: 14, borderRadius: 'var(--radius-md)', border: '1px solid var(--red-200)' }}>
                                    <div style={{ fontWeight: 700, fontSize: 12, color: 'var(--red-700)', marginBottom: 6 }}>
                                        ⚠️ Flagged Risk Anomalies:
                                    </div>
                                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: 'var(--red-700)', lineHeight: 1.5 }}>
                                        {result.risk_flags.map((flag, idx) => (
                                            <li key={idx}>{flag}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Right Column: Recent Verifications / Samples */}
                <SampleOutputs onSelectSample={handleSampleSelect} currentPortal="verifier" />
            </div>
        </div>
    )
}
