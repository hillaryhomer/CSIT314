// Navigation metadata. Account, company, project and category records live in SQLite.
export type Role = 'admin' | 'designer' | 'customer' | 'manager';
export type ScreenLink = {label:string;path:string;icon:string};
export const roles:Record<Role,{label:string;name:string;home:string;nav:ScreenLink[]}>={
 admin:{label:'User Admin',name:'Marcus Hale',home:'/admin',nav:[{label:'Overview',path:'/admin',icon:'dashboard'},{label:'User Profiles',path:'/admin/profiles',icon:'profiles'},{label:'User Accounts',path:'/admin/accounts',icon:'users'}]},
 designer:{label:'Interior Designer',name:'Studio Kanso',home:'/designer',nav:[{label:'Overview',path:'/designer',icon:'dashboard'},{label:'Company Information',path:'/designer/company',icon:'company'},{label:'Current Projects',path:'/designer/current',icon:'projects'},{label:'Past Projects',path:'/designer/past',icon:'archive'},{label:'Project Analytics',path:'/designer/analytics',icon:'analytics'}]},
 customer:{label:'Customer',name:'Eleanor Vance',home:'/',nav:[{label:'Discover Projects',path:'/',icon:'discover'},{label:'My Favourites',path:'/favourites',icon:'heart'}]},
 manager:{label:'Platform Manager',name:'Priya Raman',home:'/manager',nav:[{label:'Overview',path:'/manager',icon:'dashboard'},{label:'IDP Categories',path:'/manager/categories',icon:'categories'},{label:'Reports',path:'/manager/reports',icon:'analytics'}]}
};
export type RecordRow=Record<string,string>;
export const storyCoverage=[
 ['01–05','/admin/profiles','Persistent create, view, update, suspend and name search'],['06–08','/admin/accounts','Persistent create, view and update accounts'],['09–10','/admin/accounts','Persistent account suspension and username/email search'],['11–12, 18–19, 35–36, 47–48','/login; /logout','Shared database-backed login and logout'],['13–17','/designer/company','Persistent company CRUD and owner-scoped keyword search'],['20–24','/designer/current','Persistent Current project CRUD, image storage and search'],['25–29','/designer/past','Persistent Past project CRUD, image storage and search'],['30–32','/','Live keyword/category/style search, details and persistent favourites'],['33–34','/favourites','Private persistent favourite list and keyword search'],['37–38','/designer/analytics','Persistent customer detail views and unique saved shortlist totals'],['39–43','/manager/categories','Persistent shared category create, view, update, soft delete and search'],['44–46','/manager/reports','Real calendar reports from retained project creation and customer view events']
];
