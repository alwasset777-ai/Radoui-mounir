import React, { useRef } from 'react';
import { ClientProfile, MOROCCAN_CITIES, PropertyType, TransactionType, MediaItem } from '../types';
import { 
  User, Phone, Mail, MapPin, Banknote, FileText, Facebook, Instagram, Linkedin, 
  Map, Share2, Youtube, Twitter, Video, Globe, Upload, Image, Trash2, X,
  Armchair, Utensils, Bath, Car, Waves, Flower2, Sun, Droplets, TreeDeciduous,
  Tractor, Sprout, ArrowUpDown, Building2, Star, Coffee, Presentation
} from './Icons';

interface ClientFormProps {
  data: ClientProfile;
  onChange: (field: keyof ClientProfile, value: any) => void;
}

const ClientForm: React.FC<ClientFormProps> = ({ data, onChange }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    let parsedValue: any = value;

    if (type === 'number') {
      parsedValue = parseFloat(value) || 0;
    }

    onChange(name as keyof ClientProfile, parsedValue);
  };

  const handleCheckbox = (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(e.target.name as keyof ClientProfile, e.target.checked);
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newMedia: MediaItem[] = Array.from(e.target.files).map(file => ({
        id: Math.random().toString(36).substr(2, 9),
        url: URL.createObjectURL(file),
        type: file.type.startsWith('video/') ? 'video' : 'image',
        name: file.name
      }));

      onChange('media', [...data.media, ...newMedia]);
      
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const removeMedia = (id: string) => {
    const updatedMedia = data.media.filter(item => item.id !== id);
    onChange('media', updatedMedia);
  };

  // Logic for field visibility
  const isResidential = [PropertyType.APARTMENT, PropertyType.VILLA, PropertyType.RIAD, PropertyType.DUPLEX, PropertyType.PENTHOUSE].includes(data.propertyType);
  const isOffice = data.propertyType === PropertyType.OFFICE;
  const isLand = data.propertyType === PropertyType.LAND;
  const isAgricultural = [PropertyType.FARM, PropertyType.AGRICULTURAL_LAND].includes(data.propertyType);
  const isHotel = data.propertyType === PropertyType.HOTEL;
  
  const isVilla = data.propertyType === PropertyType.VILLA;
  const isPenthouse = data.propertyType === PropertyType.PENTHOUSE;

  // Logic for price label based on Transaction Type
  const getPriceLabel = () => {
    switch (data.transactionType) {
      case TransactionType.RENTAL:
      case TransactionType.MANAGEMENT:
        return 'Loyer Mensuel (MAD)';
      case TransactionType.KEY_MONEY:
        return 'Prix du Sarout (MAD)';
      case TransactionType.PLEDGE:
        return 'Montant Rhena (MAD)';
      case TransactionType.SALE:
        return 'Prix de Vente (MAD)';
      case TransactionType.PURCHASE:
        return 'Budget Achat (MAD)';
      default:
        return 'Budget / Prix (MAD)';
    }
  };

  const priceLabel = getPriceLabel();

  return (
    <div className="bg-white p-6 rounded-xl shadow-md border border-slate-100">
      <h2 className="text-xl font-bold text-morocco-green mb-6 flex items-center gap-2 uppercase">
        <User className="w-5 h-5" />
        INFORMATION CLIENS ET BIENS
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Identité & Contact */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider border-b pb-2">Identité & Contact</h3>
          <div className="grid grid-cols-2 gap-4">
             <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Prénom</label>
                <input
                  type="text"
                  name="firstName"
                  value={data.firstName}
                  onChange={handleChange}
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-morocco-green focus:border-transparent outline-none"
                  placeholder="Ex: Mohammed"
                />
             </div>
             <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nom</label>
                <input
                  type="text"
                  name="lastName"
                  value={data.lastName}
                  onChange={handleChange}
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-morocco-green focus:border-transparent outline-none"
                  placeholder="Ex: Benali"
                />
             </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Phone className="w-3 h-3"/> Téléphone</label>
            <input
              type="tel"
              name="phone"
              value={data.phone}
              onChange={handleChange}
              className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-morocco-green focus:border-transparent outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Mail className="w-3 h-3"/> Email</label>
            <input
              type="email"
              name="email"
              value={data.email}
              onChange={handleChange}
              className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-morocco-green focus:border-transparent outline-none"
              placeholder="client@exemple.com"
            />
          </div>

           {/* Réseaux Sociaux */}
           <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 mt-2 space-y-3">
              <label className="block text-xs font-bold text-slate-500 uppercase flex items-center gap-1">
                <Share2 className="w-3 h-3" /> Réseaux Sociaux & Web
              </label>
              <div className="grid grid-cols-1 gap-3">
                <div className="flex items-center gap-2">
                  <Facebook className="w-4 h-4 text-blue-600 shrink-0" />
                  <input
                      type="text"
                      name="facebook"
                      value={data.facebook}
                      onChange={handleChange}
                      placeholder="Facebook"
                      className="w-full p-1.5 text-sm border border-slate-300 rounded focus:border-morocco-green outline-none"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Instagram className="w-4 h-4 text-pink-600 shrink-0" />
                  <input
                      type="text"
                      name="instagram"
                      value={data.instagram}
                      onChange={handleChange}
                      placeholder="Instagram (@user)"
                      className="w-full p-1.5 text-sm border border-slate-300 rounded focus:border-morocco-green outline-none"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Linkedin className="w-4 h-4 text-blue-800 shrink-0" />
                  <input
                      type="text"
                      name="linkedin"
                      value={data.linkedin}
                      onChange={handleChange}
                      placeholder="LinkedIn"
                      className="w-full p-1.5 text-sm border border-slate-300 rounded focus:border-morocco-green outline-none"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Youtube className="w-4 h-4 text-red-600 shrink-0" />
                  <input
                      type="text"
                      name="youtube"
                      value={data.youtube}
                      onChange={handleChange}
                      placeholder="YouTube Channel"
                      className="w-full p-1.5 text-sm border border-slate-300 rounded focus:border-morocco-green outline-none"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Video className="w-4 h-4 text-black shrink-0" />
                  <input
                      type="text"
                      name="tiktok"
                      value={data.tiktok}
                      onChange={handleChange}
                      placeholder="TikTok (@user)"
                      className="w-full p-1.5 text-sm border border-slate-300 rounded focus:border-morocco-green outline-none"
                  />
                </div>
                 <div className="flex items-center gap-2">
                  <Twitter className="w-4 h-4 text-slate-800 shrink-0" />
                  <input
                      type="text"
                      name="twitter"
                      value={data.twitter}
                      onChange={handleChange}
                      placeholder="X (Twitter)"
                      className="w-full p-1.5 text-sm border border-slate-300 rounded focus:border-morocco-green outline-none"
                  />
                </div>
                 <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-slate-600 shrink-0" />
                  <input
                      type="text"
                      name="website"
                      value={data.website}
                      onChange={handleChange}
                      placeholder="Site Web personnel"
                      className="w-full p-1.5 text-sm border border-slate-300 rounded focus:border-morocco-green outline-none"
                  />
                </div>
              </div>
           </div>
        </div>

        {/* Recherche & Localisation */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider border-b pb-2">Bien & Localisation</h3>
          
          <div className="grid grid-cols-2 gap-4">
             <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Transaction</label>
                <select
                  name="transactionType"
                  value={data.transactionType}
                  onChange={handleChange}
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-morocco-green focus:border-transparent outline-none bg-white"
                >
                  {Object.values(TransactionType).map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
             </div>
             <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Type de résidence</label>
                <select
                  name="propertyType"
                  value={data.propertyType}
                  onChange={handleChange}
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-morocco-green focus:border-transparent outline-none bg-white"
                >
                   {Object.values(PropertyType).map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
             </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
               <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><MapPin className="w-3 h-3"/> Ville</label>
                <select
                  name="city"
                  value={data.city}
                  onChange={handleChange}
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-morocco-green focus:border-transparent outline-none bg-white"
                >
                   {MOROCCAN_CITIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
            </div>
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Localisation / Secteur</label>
                <input
                  type="text"
                  name="location"
                  value={data.location}
                  onChange={handleChange}
                  placeholder="Ex: Centre Ville, Près de la gare..."
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-morocco-green focus:border-transparent outline-none"
                />
            </div>
          </div>

          {/* DÉTAILS SPÉCIFIQUES (CONDITIONNELS) */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-4">
             <h4 className="text-xs font-bold text-slate-500 uppercase flex items-center gap-2">
                <FileText className="w-3 h-3" /> Caractéristiques du Bien
             </h4>
             
             <div className="grid grid-cols-2 gap-4">
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      {isAgricultural ? 'Surface (Hectares)' : 'Surface (m²)'}
                    </label>
                    <input
                      type="number"
                      name="minSurface"
                      value={data.minSurface}
                      onChange={handleChange}
                      className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                    />
                </div>

                {/* CHAMPS RÉSIDENTIELS (Appart, Villa, etc) */}
                {isResidential && (
                  <>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><User className="w-3 h-3"/> Chambres</label>
                         <input
                          type="number"
                          name="bedrooms"
                          value={data.bedrooms}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Armchair className="w-3 h-3"/> Salons</label>
                         <input
                          type="number"
                          name="livingRooms"
                          value={data.livingRooms}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Bath className="w-3 h-3"/> Salles de bain</label>
                         <input
                          type="number"
                          name="bathrooms"
                          value={data.bathrooms}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Utensils className="w-3 h-3"/> Cuisines</label>
                         <input
                          type="number"
                          name="kitchens"
                          value={data.kitchens}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Sun className="w-3 h-3"/> Balcons</label>
                         <input
                          type="number"
                          name="balconies"
                          value={data.balconies}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Sun className="w-3 h-3"/> Terrasses</label>
                         <input
                          type="number"
                          name="terraces"
                          value={data.terraces}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Car className="w-3 h-3"/> Garage (Qté)</label>
                         <input
                          type="number"
                          name="garage"
                          value={data.garage}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Car className="w-3 h-3"/> Parking (Qté)</label>
                         <input
                          type="number"
                          name="parking"
                          value={data.parking}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Building2 className="w-3 h-3"/> Étage</label>
                         <input
                          type="number"
                          name="floor"
                          value={data.floor}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                  </>
                )}
                
                {/* CHAMPS HOTEL */}
                {isHotel && (
                  <>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Star className="w-3 h-3"/> Étoiles</label>
                         <input
                          type="number"
                          name="stars"
                          value={data.stars}
                          onChange={handleChange}
                          placeholder="1-5"
                          min="0"
                          max="7"
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Building2 className="w-3 h-3"/> Nbr Chambres</label>
                         <input
                          type="number"
                          name="bedrooms"
                          value={data.bedrooms}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div className="col-span-2 grid grid-cols-2 gap-4">
                         <div className="flex items-center gap-2">
                            <input 
                              type="checkbox" 
                              id="restaurant" 
                              name="restaurant"
                              checked={data.restaurant}
                              onChange={handleCheckbox}
                              className="w-4 h-4 text-morocco-green border-gray-300 rounded focus:ring-morocco-green"
                            />
                            <label htmlFor="restaurant" className="text-sm font-medium text-slate-700 flex items-center gap-1"><Utensils className="w-3 h-3"/> Restaurant</label>
                         </div>
                         <div className="flex items-center gap-2">
                            <input 
                              type="checkbox" 
                              id="cafe" 
                              name="cafe"
                              checked={data.cafe}
                              onChange={handleCheckbox}
                              className="w-4 h-4 text-morocco-green border-gray-300 rounded focus:ring-morocco-green"
                            />
                            <label htmlFor="cafe" className="text-sm font-medium text-slate-700 flex items-center gap-1"><Coffee className="w-3 h-3"/> Café</label>
                         </div>
                         <div className="flex items-center gap-2">
                            <input 
                              type="checkbox" 
                              id="spa" 
                              name="spa"
                              checked={data.spa}
                              onChange={handleCheckbox}
                              className="w-4 h-4 text-morocco-green border-gray-300 rounded focus:ring-morocco-green"
                            />
                            <label htmlFor="spa" className="text-sm font-medium text-slate-700 flex items-center gap-1"><Waves className="w-3 h-3"/> Spa / Hammam</label>
                         </div>
                         <div className="flex items-center gap-2">
                            <input 
                              type="checkbox" 
                              id="conferenceRoom" 
                              name="conferenceRoom"
                              checked={data.conferenceRoom}
                              onChange={handleCheckbox}
                              className="w-4 h-4 text-morocco-green border-gray-300 rounded focus:ring-morocco-green"
                            />
                            <label htmlFor="conferenceRoom" className="text-sm font-medium text-slate-700 flex items-center gap-1"><Presentation className="w-3 h-3"/> Salle Conf.</label>
                         </div>
                         <div className="flex items-center gap-2">
                            <input 
                              type="checkbox" 
                              id="pool" 
                              name="pool"
                              checked={data.pool}
                              onChange={handleCheckbox}
                              className="w-4 h-4 text-morocco-green border-gray-300 rounded focus:ring-morocco-green"
                            />
                            <label htmlFor="pool" className="text-sm font-medium text-slate-700 flex items-center gap-1"><Waves className="w-3 h-3"/> Piscine</label>
                         </div>
                     </div>
                  </>
                )}
                
                {/* CHAMPS BUREAU / COMMERCE */}
                {isOffice && (
                  <>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Building2 className="w-3 h-3"/> Étage</label>
                         <input
                          type="number"
                          name="floor"
                          value={data.floor}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Bath className="w-3 h-3"/> Salles de bain</label>
                         <input
                          type="number"
                          name="bathrooms"
                          value={data.bathrooms}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Utensils className="w-3 h-3"/> Cuisines</label>
                         <input
                          type="number"
                          name="kitchens"
                          value={data.kitchens}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Sun className="w-3 h-3"/> Balcons</label>
                         <input
                          type="number"
                          name="balconies"
                          value={data.balconies}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Car className="w-3 h-3"/> Parking (Qté)</label>
                         <input
                          type="number"
                          name="parking"
                          value={data.parking}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                  </>
                )}

                 {/* CHAMPS AGRICOLES (Ferme, Terrain Agricole) */}
                 {isAgricultural && (
                   <>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Droplets className="w-3 h-3"/> Puits</label>
                         <input
                          type="number"
                          name="wells"
                          value={data.wells}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Droplets className="w-3 h-3"/> Châteaux d'eau</label>
                         <input
                          type="number"
                          name="waterTowers"
                          value={data.waterTowers}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><TreeDeciduous className="w-3 h-3"/> Nbr. Arbres</label>
                         <input
                          type="number"
                          name="trees"
                          value={data.trees}
                          onChange={handleChange}
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                      <div className="col-span-2">
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Sprout className="w-3 h-3"/> Types d'arbres</label>
                         <input
                          type="text"
                          name="treeTypes"
                          value={data.treeTypes}
                          onChange={handleChange}
                          placeholder="Ex: Oliviers, Agrumes..."
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                     <div className="col-span-2">
                        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><Tractor className="w-3 h-3"/> Autres Infrastructures</label>
                         <input
                          type="text"
                          name="infrastructure"
                          value={data.infrastructure}
                          onChange={handleChange}
                          placeholder="Ex: Maison gardien, écurie, hangar..."
                          className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                        />
                     </div>
                   </>
                 )}
             </div>

             {/* OPTIONS SUPPLEMENTAIRES (Checkbox) */}
             
             {/* VILLA & PENTHOUSE */}
             {(isVilla || isPenthouse) && (
                <div className="grid grid-cols-2 gap-4 mt-2 pt-2 border-t border-slate-200">
                   <div className="flex items-center gap-2">
                      <input 
                        type="checkbox" 
                        id="pool" 
                        name="pool"
                        checked={data.pool}
                        onChange={handleCheckbox}
                        className="w-4 h-4 text-morocco-green border-gray-300 rounded focus:ring-morocco-green"
                      />
                      <label htmlFor="pool" className="text-sm font-medium text-slate-700 flex items-center gap-1"><Waves className="w-3 h-3"/> Piscine</label>
                   </div>
                   {isVilla && (
                     <div className="flex items-center gap-2">
                        <input 
                          type="checkbox" 
                          id="garden" 
                          name="garden"
                          checked={data.garden}
                          onChange={handleCheckbox}
                          className="w-4 h-4 text-morocco-green border-gray-300 rounded focus:ring-morocco-green"
                        />
                        <label htmlFor="garden" className="text-sm font-medium text-slate-700 flex items-center gap-1"><Flower2 className="w-3 h-3"/> Jardin</label>
                     </div>
                   )}
                </div>
             )}

             {/* ASCENSEUR (Residential, Penthouse, Office) */}
             {(isResidential || isOffice) && (
                <div className="grid grid-cols-2 gap-4 mt-2 pt-2 border-t border-slate-200">
                   <div className="flex items-center gap-2">
                      <input 
                        type="checkbox" 
                        id="elevator" 
                        name="elevator"
                        checked={data.elevator}
                        onChange={handleCheckbox}
                        className="w-4 h-4 text-morocco-green border-gray-300 rounded focus:ring-morocco-green"
                      />
                      <label htmlFor="elevator" className="text-sm font-medium text-slate-700 flex items-center gap-1"><ArrowUpDown className="w-3 h-3"/> Ascenseur</label>
                   </div>
                </div>
             )}

              {/* OPTIONS AGRICOLE (Checkbox) */}
             {isAgricultural && (
                <div className="grid grid-cols-2 gap-4 mt-2 pt-2 border-t border-slate-200">
                   <div className="flex items-center gap-2">
                      <input 
                        type="checkbox" 
                        id="dripIrrigation" 
                        name="dripIrrigation"
                        checked={data.dripIrrigation}
                        onChange={handleCheckbox}
                        className="w-4 h-4 text-morocco-green border-gray-300 rounded focus:ring-morocco-green"
                      />
                      <label htmlFor="dripIrrigation" className="text-sm font-medium text-slate-700 flex items-center gap-1"><Droplets className="w-3 h-3"/> Goutte à goutte</label>
                   </div>
                </div>
             )}
          </div>

          <div className="grid grid-cols-1 gap-4">
             <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nationalité</label>
                <input
                  type="text"
                  name="nationality"
                  value={data.nationality}
                  onChange={handleChange}
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-morocco-green focus:border-transparent outline-none"
                />
             </div>
          </div>

          <div>
               <label className="block text-sm font-medium text-slate-700 mb-1">Quartiers préférés</label>
               <input
                  type="text"
                  name="preferredNeighborhoods"
                  value={data.preferredNeighborhoods}
                  onChange={handleChange}
                  placeholder="Ex: Guéliz, Racine..."
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-morocco-green focus:border-transparent outline-none"
                />
            </div>

          {/* Géolocalisation Précise */}
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-2">
             <label className="block text-xs font-bold text-slate-500 uppercase flex items-center gap-1">
                <Map className="w-3 h-3" /> Géolocalisation du bien (Optionnel)
             </label>
             <input
                type="text"
                name="googleMapsLink"
                value={data.googleMapsLink}
                onChange={handleChange}
                placeholder="Lien Google Maps (https://maps.google...)"
                className="w-full p-2 text-sm border border-slate-300 rounded focus:border-morocco-green outline-none"
             />
             <div className="flex gap-2">
                <input
                    type="text"
                    name="latitude"
                    value={data.latitude}
                    onChange={handleChange}
                    placeholder="Latitude"
                    className="w-1/2 p-2 text-sm border border-slate-300 rounded focus:border-morocco-green outline-none"
                />
                <input
                    type="text"
                    name="longitude"
                    value={data.longitude}
                    onChange={handleChange}
                    placeholder="Longitude"
                    className="w-1/2 p-2 text-sm border border-slate-300 rounded focus:border-morocco-green outline-none"
                />
             </div>
          </div>

           <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <label className="block text-sm font-medium text-slate-700 mb-2 flex items-center gap-1"><Banknote className="w-3 h-3"/> Budget Estimatif (MAD)</label>
                <div className="flex items-center gap-2">
                    <input
                      type="number"
                      name="budgetMin"
                      value={data.budgetMin}
                      onChange={handleChange}
                      placeholder="Min"
                      className="w-1/2 p-2 border border-slate-300 rounded-lg text-sm"
                    />
                    <span className="text-slate-400">-</span>
                    <input
                      type="number"
                      name="budgetMax"
                      value={data.budgetMax}
                      onChange={handleChange}
                      placeholder="Max"
                      className="w-1/2 p-2 border border-slate-300 rounded-lg text-sm"
                    />
                </div>
                
                <div className="mt-3 pt-3 border-t border-slate-200">
                    <label className="block text-sm font-medium text-slate-700 mb-1">{priceLabel}</label>
                    <input
                      type="number"
                      name="price"
                      value={data.price}
                      onChange={handleChange}
                      placeholder="Ex: 1500000"
                      className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                    />
                </div>
           </div>

           <div className="flex items-center gap-2 pt-2">
              <input 
                type="checkbox" 
                id="urgent" 
                name="urgent"
                checked={data.urgent}
                onChange={handleCheckbox}
                className="w-4 h-4 text-morocco-green border-gray-300 rounded focus:ring-morocco-green"
              />
              <label htmlFor="urgent" className="text-sm font-medium text-red-600">Recherche Urgente</label>
           </div>

        </div>
      </div>

      {/* Upload Photos/Vidéos */}
      <div className="mt-6 border-t border-slate-100 pt-6">
         <label className="block text-sm font-medium text-slate-700 mb-3 flex items-center gap-1">
            <Image className="w-4 h-4" /> Photos & Vidéos du bien
         </label>
         
         <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:bg-slate-50 transition cursor-pointer relative" onClick={() => fileInputRef.current?.click()}>
            <input 
                type="file" 
                ref={fileInputRef} 
                className="hidden" 
                multiple 
                accept="image/*,video/*" 
                onChange={handleFileChange} 
            />
            <div className="flex flex-col items-center text-slate-400">
                <Upload className="w-8 h-8 mb-2" />
                <span className="text-sm font-medium">Cliquez pour ajouter des images ou vidéos</span>
                <span className="text-xs mt-1">JPG, PNG, MP4 acceptés</span>
            </div>
         </div>

         {data.media.length > 0 && (
             <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                 {data.media.map((item) => (
                     <div key={item.id} className="relative group rounded-lg overflow-hidden border border-slate-200 h-24 bg-slate-100">
                         {item.type === 'video' ? (
                             <div className="w-full h-full flex items-center justify-center text-slate-400">
                                <Video className="w-8 h-8" />
                             </div>
                         ) : (
                             <img src={item.url} alt="preview" className="w-full h-full object-cover" />
                         )}
                         <button 
                            onClick={(e) => { e.stopPropagation(); removeMedia(item.id); }}
                            className="absolute top-1 right-1 bg-red-500 text-white p-1 rounded-full opacity-0 group-hover:opacity-100 transition"
                         >
                             <X className="w-3 h-3" />
                         </button>
                         <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[10px] p-1 truncate">
                            {item.name}
                         </div>
                     </div>
                 ))}
             </div>
         )}
      </div>

      <div className="mt-6">
        <label className="block text-sm font-medium text-slate-700 mb-1 flex items-center gap-1"><FileText className="w-3 h-3"/> Notes Complémentaires</label>
        <textarea
          name="notes"
          value={data.notes}
          onChange={handleChange}
          rows={3}
          className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-morocco-green focus:border-transparent outline-none"
          placeholder="Détails spécifiques (vue mer, étage élevé, pas de vis-à-vis...)"
        />
      </div>
    </div>
  );
};

export default ClientForm;