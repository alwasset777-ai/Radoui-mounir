import React from 'react';
import { ClientProfile, PropertyType, TransactionType } from '../types';
import { 
  Phone, Mail, Building2, Home, Facebook, Instagram, Linkedin, 
  MapPin, Map, Youtube, Twitter, Video, Globe, Image,
  Armchair, Utensils, Bath, Car, Waves, Flower2, Sun, Droplets, TreeDeciduous,
  Tractor, Sprout, ArrowUpDown, Star, Coffee, Presentation
} from 'lucide-react';

interface ClientCardProps {
  data: ClientProfile;
}

const ClientCard: React.FC<ClientCardProps> = ({ data }) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fr-MA', { style: 'currency', currency: 'MAD', maximumFractionDigits: 0 }).format(amount);
  };

  const hasSocials = data.facebook || data.instagram || data.linkedin || data.youtube || data.tiktok || data.twitter || data.website;
  const hasGeo = data.googleMapsLink || (data.latitude && data.longitude);
  const hasMedia = data.media && data.media.length > 0;

  const isResidential = [PropertyType.APARTMENT, PropertyType.VILLA, PropertyType.RIAD, PropertyType.DUPLEX, PropertyType.PENTHOUSE].includes(data.propertyType);
  const isOffice = data.propertyType === PropertyType.OFFICE;
  const isAgricultural = [PropertyType.FARM, PropertyType.AGRICULTURAL_LAND].includes(data.propertyType);
  const isLand = data.propertyType === PropertyType.LAND;
  const isHotel = data.propertyType === PropertyType.HOTEL;
  
  const isVilla = data.propertyType === PropertyType.VILLA;
  const isPenthouse = data.propertyType === PropertyType.PENTHOUSE;

  const getPriceLabel = () => {
    switch (data.transactionType) {
      case TransactionType.RENTAL:
      case TransactionType.MANAGEMENT:
        return 'Loyer';
      case TransactionType.KEY_MONEY:
        return 'Sarout';
      case TransactionType.PLEDGE:
        return 'Rhena';
      case TransactionType.SALE:
      case TransactionType.PURCHASE:
        return 'Prix';
      default:
        return 'Prix';
    }
  };

  const priceLabel = getPriceLabel();

  return (
    <div id="printable-card" className="bg-white p-8 rounded-xl shadow-lg border-t-4 border-morocco-green relative overflow-hidden">
      {/* Watermark effect */}
      <div className="absolute top-0 right-0 opacity-5 pointer-events-none transform translate-x-1/3 -translate-y-1/3">
        <Building2 className="w-64 h-64 text-morocco-green" />
      </div>
      
      <div className="flex justify-between items-start mb-6 border-b border-slate-100 pb-4">
         <div className="flex items-center gap-4">
            {/* Logo Placeholder in Header */}
            <div className="w-20 h-20 flex-shrink-0">
                 <img src="logo.png" alt="Logo AL WASSET 777" className="w-full h-full object-contain" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-slate-800">{data.firstName} {data.lastName.toUpperCase()}</h2>
              <p className="text-morocco-gold font-medium text-sm uppercase tracking-wide">{data.nationality}</p>
            </div>
         </div>
        <div className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${data.urgent ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'}`}>
          {data.urgent ? 'Urgent' : 'Standard'}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="space-y-3">
           <div className="flex items-center gap-3 text-slate-600">
              <Phone className="w-4 h-4 text-morocco-green" />
              <span className="font-medium">{data.phone || '-'}</span>
           </div>
           <div className="flex items-center gap-3 text-slate-600">
              <Mail className="w-4 h-4 text-morocco-green" />
              <span className="truncate text-sm">{data.email || '-'}</span>
           </div>
        </div>

        {hasSocials && (
            <div className="flex items-center gap-2 justify-end md:justify-start flex-wrap">
                {data.facebook && (
                    <a href={data.facebook.startsWith('http') ? data.facebook : `https://facebook.com/${data.facebook}`} target="_blank" rel="noreferrer" className="bg-blue-50 p-2 rounded-full text-blue-600 hover:bg-blue-100 transition">
                        <Facebook className="w-4 h-4" />
                    </a>
                )}
                {data.instagram && (
                    <a href={data.instagram.startsWith('http') ? data.instagram : `https://instagram.com/${data.instagram.replace('@','')}`} target="_blank" rel="noreferrer" className="bg-pink-50 p-2 rounded-full text-pink-600 hover:bg-pink-100 transition">
                        <Instagram className="w-4 h-4" />
                    </a>
                )}
                {data.linkedin && (
                    <a href={data.linkedin.startsWith('http') ? data.linkedin : `https://linkedin.com/in/${data.linkedin}`} target="_blank" rel="noreferrer" className="bg-blue-50 p-2 rounded-full text-blue-800 hover:bg-blue-100 transition">
                        <Linkedin className="w-4 h-4" />
                    </a>
                )}
                {data.youtube && (
                    <a href={data.youtube.startsWith('http') ? data.youtube : `https://youtube.com/${data.youtube}`} target="_blank" rel="noreferrer" className="bg-red-50 p-2 rounded-full text-red-600 hover:bg-red-100 transition">
                        <Youtube className="w-4 h-4" />
                    </a>
                )}
                {data.tiktok && (
                    <a href={data.tiktok.startsWith('http') ? data.tiktok : `https://tiktok.com/@${data.tiktok.replace('@','')}`} target="_blank" rel="noreferrer" className="bg-slate-100 p-2 rounded-full text-black hover:bg-slate-200 transition">
                        <Video className="w-4 h-4" />
                    </a>
                )}
                {data.twitter && (
                    <a href={data.twitter.startsWith('http') ? data.twitter : `https://twitter.com/${data.twitter.replace('@','')}`} target="_blank" rel="noreferrer" className="bg-slate-100 p-2 rounded-full text-slate-900 hover:bg-slate-200 transition">
                        <Twitter className="w-4 h-4" />
                    </a>
                )}
                 {data.website && (
                    <a href={data.website.startsWith('http') ? data.website : `https://${data.website}`} target="_blank" rel="noreferrer" className="bg-slate-50 p-2 rounded-full text-slate-600 hover:bg-slate-100 transition">
                        <Globe className="w-4 h-4" />
                    </a>
                )}
            </div>
        )}
      </div>

      <div className="bg-slate-50 rounded-lg p-5 mb-6 border border-slate-200">
        <h3 className="text-sm font-bold text-slate-800 uppercase mb-4 flex items-center gap-2">
            <Home className="w-4 h-4 text-morocco-green" />
            Détails de la Recherche
        </h3>
        <div className="grid grid-cols-2 gap-y-4 gap-x-8 text-sm">
            <div>
                <span className="block text-slate-500 text-xs uppercase">Type</span>
                <span className="font-semibold text-slate-900">{data.transactionType} / {data.propertyType}</span>
            </div>
            <div>
                <span className="block text-slate-500 text-xs uppercase">Budget Max</span>
                <span className="font-bold text-morocco-green text-base">{formatCurrency(data.budgetMax)}</span>
            </div>
             <div>
                <span className="block text-slate-500 text-xs uppercase">Localisation</span>
                <span className="font-semibold text-slate-900 flex items-center gap-1">
                     {data.city}
                </span>
                {data.location && (
                    <span className="block text-xs text-slate-600 mt-0.5">{data.location}</span>
                )}
            </div>
             <div>
                <span className="block text-slate-500 text-xs uppercase">{priceLabel}</span>
                <span className="font-bold text-slate-900 text-base">{data.price > 0 ? formatCurrency(data.price) : '-'}</span>
            </div>
             <div>
                <span className="block text-slate-500 text-xs uppercase">Quartiers</span>
                <span className="text-slate-900">{data.preferredNeighborhoods || 'Non spécifié'}</span>
            </div>
            <div>
                <span className="block text-slate-500 text-xs uppercase">Surface {isAgricultural ? '(Ha)' : 'Min'}</span>
                <span className="font-semibold text-slate-900">{data.minSurface} {isAgricultural ? 'Hectares' : 'm²'}</span>
            </div>
        </div>
        
        {/* SPECIFIC DETAILS DISPLAY */}
        <div className="mt-6 pt-4 border-t border-slate-200 grid grid-cols-3 gap-4 text-sm">
            {isResidential && (
              <>
                <div className="flex items-center gap-2 text-slate-700">
                    <Building2 className="w-4 h-4 text-morocco-green" />
                    <span>{data.bedrooms} Ch.</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700">
                    <Armchair className="w-4 h-4 text-morocco-green" />
                    <span>{data.livingRooms} Salon(s)</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700">
                    <Bath className="w-4 h-4 text-morocco-green" />
                    <span>{data.bathrooms} SDB</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700">
                    <Utensils className="w-4 h-4 text-morocco-green" />
                    <span>{data.kitchens} Cuisine(s)</span>
                </div>
                {(data.garage > 0 || data.parking > 0) && (
                   <div className="flex items-center gap-2 text-slate-700">
                      <Car className="w-4 h-4 text-morocco-green" />
                      <span>{data.garage + data.parking} Pk/Box</span>
                   </div>
                )}
                 {(data.balconies > 0 || data.terraces > 0) && (
                   <div className="flex items-center gap-2 text-slate-700">
                      <Sun className="w-4 h-4 text-morocco-green" />
                      <span>Extérieurs</span>
                   </div>
                )}
              </>
            )}
            
            {isOffice && (
               <>
                <div className="flex items-center gap-2 text-slate-700">
                    <Building2 className="w-4 h-4 text-morocco-green" />
                    <span>Étage {data.floor}</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700">
                    <Bath className="w-4 h-4 text-morocco-green" />
                    <span>{data.bathrooms} SDB</span>
                </div>
                <div className="flex items-center gap-2 text-slate-700">
                    <Utensils className="w-4 h-4 text-morocco-green" />
                    <span>{data.kitchens} Cuisine(s)</span>
                </div>
                {data.balconies > 0 && (
                   <div className="flex items-center gap-2 text-slate-700">
                      <Sun className="w-4 h-4 text-morocco-green" />
                      <span>Balcon</span>
                   </div>
                )}
                {data.elevator && (
                   <div className="flex items-center gap-2 text-slate-700 font-medium">
                      <ArrowUpDown className="w-4 h-4 text-blue-600" />
                      <span>Ascenseur</span>
                   </div>
                )}
               </>
            )}
            
            {isHotel && (
               <>
                 <div className="flex items-center gap-2 text-slate-700 font-bold">
                    <Star className="w-4 h-4 text-morocco-gold" />
                    <span>{data.stars} Étoiles</span>
                 </div>
                 <div className="flex items-center gap-2 text-slate-700">
                    <Building2 className="w-4 h-4 text-morocco-green" />
                    <span>{data.bedrooms} Chambres</span>
                 </div>
                 {data.restaurant && (
                    <div className="flex items-center gap-2 text-slate-700">
                        <Utensils className="w-4 h-4 text-morocco-green" />
                        <span>Restaurant</span>
                    </div>
                 )}
                 {data.cafe && (
                    <div className="flex items-center gap-2 text-slate-700">
                        <Coffee className="w-4 h-4 text-morocco-green" />
                        <span>Café</span>
                    </div>
                 )}
                 {data.spa && (
                    <div className="flex items-center gap-2 text-slate-700">
                        <Waves className="w-4 h-4 text-blue-400" />
                        <span>Spa/Hammam</span>
                    </div>
                 )}
                 {data.conferenceRoom && (
                    <div className="flex items-center gap-2 text-slate-700">
                        <Presentation className="w-4 h-4 text-slate-600" />
                        <span>Salle Conf.</span>
                    </div>
                 )}
                 {data.pool && (
                    <div className="flex items-center gap-2 text-slate-700">
                        <Waves className="w-4 h-4 text-blue-500" />
                        <span>Piscine</span>
                    </div>
                 )}
               </>
            )}
            
            {(isVilla || isPenthouse) && (
              <>
                {data.pool && (
                   <div className="flex items-center gap-2 text-slate-700 font-medium">
                      <Waves className="w-4 h-4 text-blue-500" />
                      <span>Piscine</span>
                   </div>
                )}
                {data.garden && (
                   <div className="flex items-center gap-2 text-slate-700 font-medium">
                      <Flower2 className="w-4 h-4 text-green-600" />
                      <span>Jardin</span>
                   </div>
                )}
              </>
            )}

            {(isResidential || isOffice) && data.elevator && !isOffice && ( // Avoid double showing for office
               <div className="flex items-center gap-2 text-slate-700 font-medium">
                  <ArrowUpDown className="w-4 h-4 text-blue-600" />
                  <span>Ascenseur</span>
               </div>
            )}
            
            {(isResidential || isPenthouse) && data.floor > 0 && (
               <div className="flex items-center gap-2 text-slate-700 font-medium">
                  <Building2 className="w-4 h-4 text-slate-600" />
                  <span>Étage {data.floor}</span>
               </div>
            )}

            {isAgricultural && (
               <>
                 <div className="flex items-center gap-2 text-slate-700">
                    <Droplets className="w-4 h-4 text-blue-500" />
                    <span>{data.wells} Puits</span>
                 </div>
                 <div className="flex items-center gap-2 text-slate-700">
                    <Droplets className="w-4 h-4 text-slate-500" />
                    <span>{data.waterTowers} Château(x)</span>
                 </div>
                 <div className="flex items-center gap-2 text-slate-700">
                    <TreeDeciduous className="w-4 h-4 text-green-700" />
                    <span>{data.trees} Arbres</span>
                 </div>
                 {data.treeTypes && (
                    <div className="flex items-center gap-2 text-slate-700 col-span-2">
                        <Sprout className="w-4 h-4 text-green-600" />
                        <span>{data.treeTypes}</span>
                    </div>
                 )}
                 {data.dripIrrigation && (
                    <div className="flex items-center gap-2 text-slate-700 font-medium">
                        <Droplets className="w-4 h-4 text-blue-600" />
                        <span>Goutte à goutte</span>
                    </div>
                 )}
                 {data.infrastructure && (
                    <div className="flex items-center gap-2 text-slate-700 col-span-3">
                        <Tractor className="w-4 h-4 text-slate-600" />
                        <span>Infra: {data.infrastructure}</span>
                    </div>
                 )}
               </>
            )}
            
            {isLand && (
               <div className="col-span-3 text-slate-500 italic">
                 Terrain constructible, détails spécifiques à voir en notes.
               </div>
            )}
        </div>

        {hasGeo && (
            <div className="mt-6 pt-4 border-t border-slate-200">
                <h4 className="text-xs font-bold text-slate-500 uppercase mb-2 flex items-center gap-1">
                    <Map className="w-3 h-3" /> Géolocalisation Cible
                </h4>
                <div className="flex flex-wrap items-center gap-2">
                    {data.googleMapsLink && (
                        <a href={data.googleMapsLink} target="_blank" rel="noreferrer" className="text-xs bg-white border border-slate-300 px-3 py-1.5 rounded flex items-center gap-2 text-slate-700 hover:bg-slate-50 hover:text-morocco-green transition">
                            <MapPin className="w-3 h-3" /> Voir sur Google Maps
                        </a>
                    )}
                    {(data.latitude && data.longitude) && (
                        <span className="text-xs text-slate-500 font-mono bg-slate-100 px-2 py-1 rounded">
                            GPS: {data.latitude}, {data.longitude}
                        </span>
                    )}
                </div>
            </div>
        )}
      </div>

      {hasMedia && (
          <div className="mb-6">
             <h4 className="text-xs font-bold text-slate-500 uppercase mb-2 flex items-center gap-1">
                 <Image className="w-3 h-3" /> Galerie Multimédia
             </h4>
             <div className="grid grid-cols-3 gap-2">
                 {data.media.map((item) => (
                     <div key={item.id} className="aspect-square bg-slate-100 rounded-lg overflow-hidden border border-slate-200 relative">
                         {item.type === 'video' ? (
                             <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 bg-slate-50">
                                 <Video className="w-8 h-8 mb-1" />
                                 <span className="text-[10px] px-2 text-center truncate w-full">{item.name}</span>
                             </div>
                         ) : (
                             <img src={item.url} alt="Bien" className="w-full h-full object-cover" />
                         )}
                     </div>
                 ))}
             </div>
          </div>
      )}

      {data.notes && (
        <div className="mb-4">
           <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">Notes</h4>
           <p className="text-sm text-slate-600 italic bg-yellow-50 p-3 rounded border border-yellow-100">
             "{data.notes}"
           </p>
        </div>
      )}

      <div className="text-xs text-center text-slate-400 mt-8 pt-4 border-t border-slate-100">
         <p className="font-bold text-slate-600 uppercase mb-1">AL WASSET 777 IMMOBILIER</p>
         <p>Rue de paris Gallerie select N.52 Hamria Meknès</p>
         <p className="mt-2">{new Date().toLocaleDateString('fr-MA')}</p>
      </div>
    </div>
  );
};

export default ClientCard;