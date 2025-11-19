export enum TransactionType {
  PURCHASE = 'Achat',
  SALE = 'Vente',
  RENTAL = 'Location',
  KEY_MONEY = 'Sarout',
  PLEDGE = 'Rhena',
  TAKEOVER = 'Reprise',
  MANAGEMENT = 'Gérance',
}

export enum PropertyType {
  APARTMENT = 'Appartement',
  VILLA = 'Villa',
  RIAD = 'Riad',
  HOTEL = 'Hôtel',
  LAND = 'Terrain Constructible',
  AGRICULTURAL_LAND = 'Terrain Agricole',
  OFFICE = 'Bureau/Commerce',
  FARM = 'Ferme',
  DUPLEX = 'Duplex',
  PENTHOUSE = 'Penthouse',
}

export const MOROCCAN_CITIES = [
  'Agadir', 'Al Hoceïma', 'Azilal', 'Azrou', 'Beni Mellal', 'Benslimane', 'Berkane', 'Berrechid', 
  'Bouskoura', 'Bouznika', 'Casablanca', 'Chefchaouen', 'Dakhla', 'Dar Bouazza', 'Drarga', 
  'El Jadida', 'El Kelaa des Sraghna', 'Errachidia', 'Essaouira', 'Fès', 'Fnideq', 'Fquih Ben Salah', 
  'Guelmim', 'Guercif', 'Ifrane', 'Inezgane', 'Kénitra', 'Khemisset', 'Khenifra', 'Khouribga', 
  'Ksar El Kebir', 'Laâyoune', 'Larache', 'Marrakech', 'Martil', 'Meknès', 'Midelt', 'Mohammedia', 
  'Nador', 'Ouarzazate', 'Ouezzane', 'Oujda', 'Rabat', 'Safi', 'Salé', 'Sefrou', 'Settat', 
  'Sidi Kacem', 'Sidi Rahal', 'Sidi Slimane', 'Skhirat', 'Tanger', 'Tan-Tan', 'Taroudant', 'Taza', 
  'Témara', 'Tétouan', 'Tiznit', 'Youssoufia', 'Zagora', 'Autre'
].sort();

export interface MediaItem {
  id: string;
  url: string;
  type: 'image' | 'video';
  name: string;
}

export interface ClientProfile {
  firstName: string;
  lastName: string;
  phone: string;
  email: string;
  
  // Réseaux Sociaux
  facebook: string;
  instagram: string;
  linkedin: string;
  youtube: string;
  tiktok: string;
  twitter: string; // Pour X
  website: string;
  
  nationality: string;
  budgetMin: number;
  budgetMax: number;
  price: number; // Prix de vente ou Loyer mensuel cible
  
  // Localisation
  city: string;
  location: string; // Localisation / Secteur précis
  preferredNeighborhoods: string;
  // Géolocalisation précise (pour un bien ciblé ou une zone)
  googleMapsLink: string;
  latitude: string;
  longitude: string;

  transactionType: TransactionType;
  propertyType: PropertyType;
  minSurface: number;
  urgent: boolean;
  notes: string;

  // Médias
  media: MediaItem[];

  // Détails Résidentiels / Bureaux / Hôtels
  bedrooms: number; // Utilisé comme Nbr Chambres pour Hôtel
  livingRooms: number; // Salons
  bathrooms: number; // Salles de bain
  kitchens: number; // Cuisines
  balconies: number; // Balcons
  terraces: number; // Terrasses
  garage: number; // Garage (nombre de places ou box)
  parking: number; // Parking (nombre de places)
  floor: number; // Etage
  elevator: boolean; // Ascenseur

  // Détails Spécifiques Villa / Penthouse / Hôtel
  pool: boolean;
  garden: boolean;

  // Détails Spécifiques Hôtel
  stars: number; // Nombre d'étoiles
  restaurant: boolean;
  cafe: boolean;
  spa: boolean; // Spa / Hammam
  conferenceRoom: boolean;

  // Détails Agricoles (Terrain Agricole, Ferme)
  wells: number; // Puits
  waterTowers: number; // Châteaux d'eau
  trees: number; // Nombre d'arbres
  treeTypes: string; // Types d'arbres (ex: Oliviers, Agrumes)
  dripIrrigation: boolean; // Goutte à goutte
  infrastructure: string; // Autre infrastructures
}

export const INITIAL_CLIENT_PROFILE: ClientProfile = {
  firstName: '',
  lastName: '',
  phone: '+212 ',
  email: '',
  facebook: '',
  instagram: '',
  linkedin: '',
  youtube: '',
  tiktok: '',
  twitter: '',
  website: '',
  nationality: 'Marocaine',
  budgetMin: 0,
  budgetMax: 0,
  price: 0,
  city: 'Casablanca',
  location: '',
  preferredNeighborhoods: '',
  googleMapsLink: '',
  latitude: '',
  longitude: '',
  transactionType: TransactionType.PURCHASE,
  propertyType: PropertyType.APARTMENT,
  minSurface: 0,
  urgent: false,
  notes: '',
  media: [],

  // Résidentiel / Office init
  bedrooms: 2,
  livingRooms: 1,
  bathrooms: 1,
  kitchens: 1,
  balconies: 0,
  terraces: 0,
  garage: 0,
  parking: 0,
  floor: 0,
  elevator: false,

  // Villa / Penthouse / Hôtel init
  pool: false,
  garden: false,
  
  // Hôtel init
  stars: 0,
  restaurant: false,
  cafe: false,
  spa: false,
  conferenceRoom: false,

  // Agricole init
  wells: 0,
  waterTowers: 0,
  trees: 0,
  treeTypes: '',
  dripIrrigation: false,
  infrastructure: '',
};