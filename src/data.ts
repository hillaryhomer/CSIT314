// Read-only display fixtures. No account, permission, persistence or report engine.
export type Role = 'admin' | 'designer' | 'customer' | 'manager';
export type ScreenLink = {label:string;path:string;icon:string};
export const roles:Record<Role,{label:string;name:string;home:string;nav:ScreenLink[]}>={
 admin:{label:'User Admin',name:'Marcus Hale',home:'/admin',nav:[{label:'Overview',path:'/admin',icon:'dashboard'},{label:'User Profiles',path:'/admin/profiles',icon:'profiles'},{label:'User Accounts',path:'/admin/accounts',icon:'users'}]},
 designer:{label:'Interior Designer',name:'Studio Kanso',home:'/designer',nav:[{label:'Overview',path:'/designer',icon:'dashboard'},{label:'Company Information',path:'/designer/company',icon:'company'},{label:'Current Projects',path:'/designer/current',icon:'projects'},{label:'Past Projects',path:'/designer/past',icon:'archive'},{label:'Project Analytics',path:'/designer/analytics',icon:'analytics'}]},
 customer:{label:'Customer',name:'Eleanor Vance',home:'/',nav:[{label:'Discover Projects',path:'/',icon:'discover'},{label:'My Favourites',path:'/favourites',icon:'heart'}]},
 manager:{label:'Platform Manager',name:'Priya Raman',home:'/manager',nav:[{label:'Overview',path:'/manager',icon:'dashboard'},{label:'IDP Categories',path:'/manager/categories',icon:'categories'},{label:'Reports',path:'/manager/reports',icon:'analytics'}]}
};
export type RecordRow=Record<string,string>;
export const profiles:RecordRow[]=[
 {id:'UP001',name:'Interior Designer',role:'Interior Designer',permissions:'Project Management',status:'Active'},
 {id:'UP002',name:'Customer',role:'Customer',permissions:'Standard Access',status:'Active'},
 {id:'UP003',name:'Platform Manager',role:'Platform Manager',permissions:'Administrative Access',status:'Suspended'},
 {id:'UP004',name:'User Admin',role:'User Admin',permissions:'User Management',status:'Active'}
];
export const accounts:RecordRow[]=[{id:'UA001',username:'designer01',email:'designer01@example.com',profile:'Interior Designer',status:'Active'},{id:'UA002',username:'customer01',email:'customer01@example.com',profile:'Customer',status:'Active'},{id:'UA003',username:'manager01',email:'manager01@example.com',profile:'Platform Manager',status:'Active'}];
export const categories:RecordRow[]=[{id:'CAT001',name:'Residential',description:'Homes and apartments',count:'4'},{id:'CAT002',name:'Commercial',description:'Offices and retail',count:'0'},{id:'CAT003',name:'Hospitality',description:'Cafés, restaurants and boutique hotels',count:'0'}];
export const company:RecordRow={name:'Studio Kanso Architects',address:'12 Rokeby Road, Subiaco WA 6008',contact:'hello@studiokanso.com.au',description:'Residential interior design studio specialising in calm, material-led Japandi homes.'};
export type Project={id:string;title:string;category:string;style:string;studio:string;city:string;status:'Current'|'Past';image:string;description:string;views:number;shortlists:number;room:string};
export const projects:Project[]=[
 {id:'P001',title:'The Kyoto Residence',category:'Residential',style:'Japandi Minimal',studio:'Studio Kanso Architects',city:'Subiaco, Perth',status:'Current',image:'/images/interior-1.jpg',description:'Textured limestone, curved bouclé furnishings and Japanese garden vistas create a calm contemporary home. Warm walnut joinery brings a natural rhythm to every room.',views:120,shortlists:18,room:'Living Spaces'},
 {id:'P002',title:'Travertine Fluted Kitchen',category:'Residential',style:'Warm Organic Modern',studio:'Atelier Vane Design',city:'Cottesloe, Perth',status:'Current',image:'/images/interior-2.jpg',description:'Dark fluted oak joinery pairs with honed travertine counters, patinated bronze fittings and warm concealed lighting.',views:0,shortlists:0,room:'Kitchens'},
 {id:'P003',title:'Lime Plaster Sanctuary',category:'Residential',style:'Wabi-Sabi',studio:'Soren & Co. Studio',city:'Fitzroy, Melbourne',status:'Past',image:'/images/interior-3.jpg',description:'Mineral lime plaster on soft curves, natural linen drapes and a timber platform bed in filtered morning light.',views:342,shortlists:41,room:'Primary Suites'},
 {id:'P004',title:'Mt Lawley Apartment',category:'Residential',style:'Mid-Century Restored',studio:'Studio Kanso Architects',city:'Mt Lawley, Perth',status:'Past',image:'/images/interior-2.jpg',description:'A restored apartment with walnut joinery, terrazzo and restrained modern finishes.',views:86,shortlists:9,room:'Living Spaces'}
];
export const storyCoverage=[
 ['01–05','/admin/profiles','Create, view, update, suspend and search profiles'],['06–10','/admin/accounts','Create, view, update, suspend and search accounts'],['11–12, 18–19, 35–36, 47–48','/login; /logout','Shared login and logout screen previews'],['13–17','/designer/company','Create, view, update, delete and search company information'],['20–24','/designer/current','Current project CRUD and search layouts'],['25–29','/designer/past','Past project CRUD and search layouts'],['30–32','/','Discover, project details and save-to-favourites layouts'],['33–34','/favourites','Favourite list and keyword search layouts'],['37–38','/designer/analytics','Project view and shortlist display'],['39–43','/manager/categories','Category CRUD and search layouts'],['44–46','/manager/reports','Daily, weekly and monthly report preview layouts']
];
