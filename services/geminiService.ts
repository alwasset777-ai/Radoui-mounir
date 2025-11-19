import { GoogleGenAI } from "@google/genai";
import { ClientProfile, PropertyType } from '../types';

const apiKey = process.env.API_KEY || '';

// Initialize client strictly with the API key from env
const ai = new GoogleGenAI({ apiKey });

export const generateClientSummary = async (profile: ClientProfile): Promise<string> => {
  try {
    const model = 'gemini-2.5-flash';
    const socialPresence = [
        profile.facebook && 'Facebook', 
        profile.instagram && 'Instagram', 
        profile.linkedin && 'LinkedIn',
        profile.youtube && 'YouTube',
        profile.tiktok && 'TikTok',
        profile.twitter && 'X (Twitter)',
        profile.website && 'Site Web'
    ].filter(Boolean).join(', ');

    // Build specific details string based on property type
    let specifics = '';
    const isResidential = [PropertyType.APARTMENT, PropertyType.VILLA, PropertyType.RIAD, PropertyType.DUPLEX, PropertyType.PENTHOUSE].includes(profile.propertyType);
    const isOffice = profile.propertyType === PropertyType.OFFICE;
    const isAgricultural = [PropertyType.FARM, PropertyType.AGRICULTURAL_LAND].includes(profile.propertyType);
    const isHotel = profile.propertyType === PropertyType.HOTEL;

    if (isResidential || isOffice) {
        if (isResidential) specifics += `\n      Configuration: ${profile.bedrooms} Ch, ${profile.livingRooms} Salon(s)`;
        specifics += `\n      Sanitaires/Cuisine: ${profile.bathrooms} SDB, ${profile.kitchens} Cuisine(s)`;
        if(profile.floor > 0) specifics += `\n      Étage: ${profile.floor}`;
        if(profile.elevator) specifics += `\n      Ascenseur: OUI`;
        if(profile.garage > 0 || profile.parking > 0) specifics += `\n      Stationnement: ${profile.garage} Garage, ${profile.parking} Parking`;
        if(profile.pool) specifics += `\n      Piscine: OUI`;
        if(profile.garden) specifics += `\n      Jardin: OUI`;
    }
    if (isHotel) {
        specifics += `\n      Hôtel: ${profile.stars} Étoiles, ${profile.bedrooms} Chambres`;
        if(profile.restaurant) specifics += `\n      Restaurant: OUI`;
        if(profile.cafe) specifics += `\n      Café: OUI`;
        if(profile.spa) specifics += `\n      Spa/Hammam: OUI`;
        if(profile.conferenceRoom) specifics += `\n      Salle Conférence: OUI`;
        if(profile.pool) specifics += `\n      Piscine: OUI`;
    }
    if (isAgricultural) {
        specifics += `\n      Agricole: ${profile.wells} Puits, ${profile.waterTowers} Châteaux d'eau, ${profile.trees} Arbres`;
        if (profile.treeTypes) specifics += `\n      Types d'arbres: ${profile.treeTypes}`;
        if (profile.dripIrrigation) specifics += `\n      Irrigation: Goutte à goutte installée`;
        if (profile.infrastructure) specifics += `\n      Infrastructures: ${profile.infrastructure}`;
    }
    
    const prompt = `
      Agis comme un agent immobilier senior au Maroc.
      Analyse la fiche client suivante et génère un résumé professionnel concis (max 100 mots) pour le CRM de l'agence.
      Mets en évidence le sérieux, le budget par rapport au marché actuel à ${profile.city} (Zone: ${profile.location}), l'urgence et la présence numérique du client (si renseignée).
      Prends en compte les détails spécifiques demandés (nbr pièces, piscine, puits, type d'agriculture, classification hôtel, etc).

      Données client :
      Nom: ${profile.firstName} ${profile.lastName}
      Type: ${profile.transactionType} de ${profile.propertyType}
      Ville: ${profile.city}
      Localisation spécifique (Secteur/Adresse): ${profile.location}
      Localisation précise (GPS/Maps): ${profile.googleMapsLink || (profile.latitude && profile.longitude) ? 'OUI' : 'NON'}
      Quartiers préférés: ${profile.preferredNeighborhoods}
      Budget Range: ${profile.budgetMin} - ${profile.budgetMax} MAD
      Prix Cible / Loyer: ${profile.price > 0 ? profile.price + ' MAD' : 'Non spécifié'}
      Surface min: ${profile.minSurface} ${isAgricultural ? 'Hectares' : 'm²'}${specifics}
      Réseaux sociaux / Web: ${socialPresence || 'Aucun'}
      Urgence: ${profile.urgent ? 'OUI' : 'NON'}
      Notes: ${profile.notes}
    `;

    const response = await ai.models.generateContent({
      model,
      contents: prompt,
    });

    return response.text || "Impossible de générer le résumé.";
  } catch (error) {
    console.error("Error generating summary:", error);
    return "Erreur lors de la génération du résumé IA.";
  }
};

export const generateRecommendations = async (profile: ClientProfile): Promise<string> => {
  try {
    const model = 'gemini-2.5-flash';
    const prompt = `
      Agis comme un expert du marché immobilier marocain.
      Basé sur les critères suivants, suggère 3 quartiers spécifiques à ${profile.city} (proche de ${profile.location} si pertinent) qui pourraient correspondre, et donne une estimation rapide si le budget est réaliste pour la configuration demandée.
      
      Critères :
      Budget Max: ${profile.budgetMax} MAD
      Prix Cible: ${profile.price > 0 ? profile.price : 'Non spécifié'}
      Type: ${profile.propertyType}
      Surface: ${profile.minSurface} m²
      Notes: ${profile.notes}
      
      Réponds en format liste à puces (Markdown). Sois direct et précis.
    `;

    const response = await ai.models.generateContent({
      model,
      contents: prompt,
    });

    return response.text || "Pas de recommandations disponibles.";
  } catch (error) {
    console.error("Error generating recommendations:", error);
    return "Erreur lors de l'analyse du marché.";
  }
};

export const generateDraftMessage = async (profile: ClientProfile): Promise<string> => {
    try {
        const model = 'gemini-2.5-flash';
        const socialContext = profile.instagram ? "J'ai vu votre profil Instagram, très intéressant." : "";
        
        const prompt = `
          Rédige un message WhatsApp court, professionnel et accueillant (en français) à envoyer à ce client pour confirmer la prise en compte de sa recherche.
          Utilise le vouvoiement. Inclus le nom du client (${profile.lastName}). Mentionne spécifiquement sa recherche de ${profile.propertyType} à ${profile.city} ${profile.location ? `(${profile.location})` : ''}.
          Mentionne brièvement un détail clé (ex: piscine, grand jardin, nombre de chambres, type de terrain, classification hôtel) si pertinent.
          ${socialContext}
          Si le client a fourni une localisation précise (Maps), confirme que nous avons bien repéré la zone.
        `;
    
        const response = await ai.models.generateContent({
          model,
          contents: prompt,
        });
    
        return response.text || "Erreur de rédaction.";
      } catch (error) {
        console.error("Error generating draft:", error);
        return "Erreur de génération du message.";
      }
}