import React, { useState } from 'react';
import { ClientProfile, INITIAL_CLIENT_PROFILE } from './types';
import ClientForm from './components/ClientForm';
import ClientCard from './components/ClientCard';
import { Sparkles, Printer, MessageCircle, Save, Building2, Loader2 } from './components/Icons';
import { generateClientSummary, generateRecommendations, generateDraftMessage } from './services/geminiService';

const App: React.FC = () => {
  const [clientData, setClientData] = useState<ClientProfile>(INITIAL_CLIENT_PROFILE);
  const [aiSummary, setAiSummary] = useState<string>('');
  const [aiRecommendations, setAiRecommendations] = useState<string>('');
  const [aiDraft, setAiDraft] = useState<string>('');
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [loadingDraft, setLoadingDraft] = useState(false);

  const handleUpdateClient = (field: keyof ClientProfile, value: any) => {
    setClientData((prev) => ({ ...prev, [field]: value }));
  };

  const handleGenerateAI = async () => {
    if (!process.env.API_KEY) {
        alert("API Key manquante. L'IA ne peut pas fonctionner.");
        return;
    }
    
    setLoadingSummary(true);
    setLoadingRecs(true);
    setLoadingDraft(true);

    // Run in parallel
    generateClientSummary(clientData).then(res => {
        setAiSummary(res);
        setLoadingSummary(false);
    });
    generateRecommendations(clientData).then(res => {
        setAiRecommendations(res);
        setLoadingRecs(false);
    });
    generateDraftMessage(clientData).then(res => {
        setAiDraft(res);
        setLoadingDraft(false);
    });
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-slate-50 pb-20 font-sans text-slate-800">
      {/* Navbar */}
      <header className="bg-morocco-green text-white sticky top-0 z-50 shadow-md">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Building2 className="w-8 h-8 text-morocco-gold" />
            <div>
              <h1 className="text-xl font-bold tracking-tight">AL WASSET 777 IMMOBILIER</h1>
              <p className="text-xs text-morocco-sand opacity-80">Gestion Fiche Client</p>
            </div>
          </div>
          <div className="flex gap-3">
            <button 
               onClick={handlePrint}
               className="flex items-center gap-2 bg-white/10 hover:bg-white/20 px-4 py-2 rounded-lg text-sm font-medium transition"
            >
              <Printer className="w-4 h-4" />
              <span className="hidden sm:inline">Imprimer</span>
            </button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left Column: Form (Input) */}
          <div className="lg:col-span-7 space-y-6 print:hidden">
             <div className="bg-blue-50 border border-blue-100 p-4 rounded-lg mb-4 flex items-start gap-3">
                <div className="bg-blue-100 p-2 rounded-full text-blue-600">
                    <Sparkles className="w-5 h-5" />
                </div>
                <div>
                    <h3 className="font-semibold text-blue-900 text-sm">Remplissage assisté</h3>
                    <p className="text-blue-700 text-sm mt-1">Remplissez les détails à gauche. Une fois terminé, cliquez sur "Analyser avec IA" pour obtenir un résumé professionnel, des recommandations de quartiers et un message de bienvenue.</p>
                </div>
             </div>

             <ClientForm data={clientData} onChange={handleUpdateClient} />
             
             <div className="flex justify-end">
                <button
                    onClick={handleGenerateAI}
                    disabled={loadingSummary || loadingRecs}
                    className="flex items-center gap-2 bg-morocco-gold hover:bg-yellow-600 text-white px-6 py-3 rounded-xl shadow-lg shadow-orange-900/10 font-bold transition transform active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {(loadingSummary || loadingRecs) ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                    Analyser avec IA Gemini
                </button>
             </div>
          </div>

          {/* Right Column: Visualization & AI Output */}
          <div className="lg:col-span-5 space-y-6">
            
            {/* The "Fiche" Card */}
            <div>
                <div className="flex items-center justify-between mb-2 print:hidden">
                   <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider">Aperçu de la Fiche</h3>
                </div>
                <ClientCard data={clientData} />
            </div>

            {/* AI Insights Section */}
            <div className="space-y-4 print:break-inside-avoid">
                
                {/* Summary */}
                <div className="bg-white p-5 rounded-xl shadow border border-slate-100">
                    <h3 className="font-bold text-morocco-green flex items-center gap-2 mb-3">
                        <Save className="w-4 h-4" /> Résumé CRM
                    </h3>
                    {loadingSummary ? (
                        <div className="flex items-center gap-2 text-sm text-slate-400 animate-pulse">
                            <Loader2 className="w-4 h-4 animate-spin" /> Génération du résumé...
                        </div>
                    ) : (
                        <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
                            {aiSummary || "En attente d'analyse..."}
                        </p>
                    )}
                </div>

                {/* Market Advice */}
                <div className="bg-white p-5 rounded-xl shadow border border-slate-100">
                     <h3 className="font-bold text-morocco-green flex items-center gap-2 mb-3">
                        <Building2 className="w-4 h-4" /> Recommandations Marché
                    </h3>
                     {loadingRecs ? (
                        <div className="flex items-center gap-2 text-sm text-slate-400 animate-pulse">
                            <Loader2 className="w-4 h-4 animate-spin" /> Analyse du marché en cours...
                        </div>
                    ) : (
                         <div className="text-sm text-slate-600 prose prose-sm max-w-none prose-ul:pl-4 prose-li:marker:text-morocco-gold">
                            {aiRecommendations ? (
                                <div dangerouslySetInnerHTML={{ 
                                    __html: aiRecommendations
                                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                        .replace(/- /g, '• ')
                                        .split('\n').join('<br/>') 
                                }} />
                            ) : (
                                "En attente d'analyse..."
                            )}
                        </div>
                    )}
                </div>

                 {/* Draft Message */}
                 <div className="bg-white p-5 rounded-xl shadow border border-slate-100">
                     <h3 className="font-bold text-morocco-green flex items-center gap-2 mb-3">
                        <MessageCircle className="w-4 h-4" /> Brouillon WhatsApp
                    </h3>
                     {loadingDraft ? (
                        <div className="flex items-center gap-2 text-sm text-slate-400 animate-pulse">
                            <Loader2 className="w-4 h-4 animate-spin" /> Rédaction en cours...
                        </div>
                    ) : (
                        <div className="bg-green-50 p-3 rounded-lg border border-green-100 relative">
                            <p className="text-sm text-slate-700 italic whitespace-pre-line">
                                {aiDraft || "En attente d'analyse..."}
                            </p>
                            {aiDraft && (
                                <button 
                                    onClick={() => navigator.clipboard.writeText(aiDraft)}
                                    className="absolute top-2 right-2 text-xs bg-white px-2 py-1 rounded border shadow-sm hover:bg-gray-50"
                                >
                                    Copier
                                </button>
                            )}
                        </div>
                    )}
                </div>

            </div>
          </div>

        </div>
      </main>

      {/* Print Styles */}
      <style>{`
        @media print {
          body * {
            visibility: hidden;
          }
          #printable-card, #printable-card * {
            visibility: visible;
          }
          #printable-card {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            margin: 0;
            padding: 20px;
            border: none;
            box-shadow: none;
          }
          .print\\:hidden {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
};

export default App;