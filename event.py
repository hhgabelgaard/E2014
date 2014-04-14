# -*- coding: utf-8 -*-
##############################################################################
#
#    DDS Member
#    Copyright (C) 2011 Hans Henrik Gabelgaard
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


import datetime
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.osv.orm import setup_modifiers

from xml.etree import ElementTree as ET
from urllib import urlopen


partmap = {('docTitle', 'name'),
           ('addressFull','street'),
           ('organizationAddress2','street2'),
           ('organizationPostalCode','zip'),
           ('City','city'),
           ('organizationEMail','email'),
           ('organizationWeb','website'),
           ('organizationPhone','phone'),
           ('organizationMobilePhone','mobile')
           
           }

econmap = {('userFirstname', 'name'),
           ('addressFull','street'),
           ('organizationAddress2','street2'),
           ('userEmail','email'),
           ('userPrivatePhone','phone'),
           ('userMobilePhone','mobile'),
           ('userMemberNumber','ref')
           
           }
class dds_camp_scoutorg(osv.osv):
    """ Scout Organizations"""
    _description = 'Scout Organizations'
    _name = 'dds_camp.scout.org'
    _order = 'name'
    _columns = {
        'name': fields.char('Name', size=128),
        'country_id': fields.many2one('res.country', 'Country'),
        'sex' : fields.char('Sex', size=128),
        'worldorg': fields.selection([('wagggs','WAGGGS'),
                                      ('wosm', 'WOSM'),
                                      ('w/w', 'WAGGGS/WOSM'),
                                      ('other','Other')],'World Organization'),
    }
dds_camp_scoutorg()

class dds_camp_municipality(osv.osv):
    """ Kommuner """
    _description = 'DK Kommuner'
    _name = 'dds_camp.municipality'
    _order = 'name'
    _columns = {
        'name': fields.char('Name', size=64),
        'number': fields.integer('Number')
    }
dds_camp_municipality()

class dds_camp_committee(osv.osv):
    """ Committee """
    _description = 'Committee'
    _name = 'dds_camp.committee'
    _inherit = 'mail.thread'
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        if name:
            # Be sure name_search is symetric to name_get
            name = name.split(' / ')[-1]
            ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
    
    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name', 'parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1] + ' / ' + name
            res.append((record['id'], name))
        return res
    
    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)
    _order = 'sequence, complete_name'
    
    _columns = {
        'name': fields.char('Name', size=64, translate=True),
        'desc': fields.text('Description', translate=True),
        'email': fields.char('Email', size=128),
        'members_ids': fields.one2many('dds_camp.event.participant', 'committee_id', 'Members'),
        'template_id': fields.many2one('email.template', 'Email Template', ondelete='set null', domain=[('model_id', '=', 'dds_camp.event.participant')]),
        'parent_id': fields.many2one('dds_camp.committee', 'Hovedudvalg'),
        'child_ids': fields.one2many('dds_camp.committee', 'parent_id', 'Underudvalg'),
        'sequence': fields.integer('Sequence', select=True, help="Gives the sequence order."),
        'complete_name': fields.function(_name_get_fnc, type="char", string='Full Name', store=True),     
        
    }
    
    
    
dds_camp_committee()

class dds_camp_area(osv.osv):
    """ Camp Area """
    _description = 'Camp Area'
    _name = 'dds_camp.area'
    
    _columns = {
        'name': fields.char('Name', size=64, translate=True),
        'desc': fields.text('Description', translate=True),
        'email': fields.char('Email', size=128),
        'group_ids': fields.one2many('event.registration', 'camparea_id', 'Troops'),
        'addgroup_id' : fields.many2one('event.registration', 'Add Troop', ondelete='set null', domain=[('state','!=', 'cancel')]),
        }
    
    def onchange_add_group(self, cr, uid, ids, addgroup_id, group_ids, context=None):
        group_ids.append([4,addgroup_id,False])
        print "addgroup", group_ids
        return {'value': {'group_ids': group_ids,
                          'addgroup_id' : None
                          }
                }
dds_camp_area()
    
class dds_camp_friendship(osv.osv):
    """ Frinedship groups """
    _description = 'Friendship Grouping'
    _name = 'dds_camp.friendship'
    
    def _calc_name(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            name = "" 
            for grp in record.group_ids:
                name = name + grp.name + " / "
            name = name[:-3]
            res[record.id] = {'name': name}
        return res
    
    _columns = {
        'name': fields.function(_calc_name, type = 'char', string='Name', size=128, method=True, multi='FR'),
        'desc': fields.text('Description', translate=True),
        'email': fields.char('Email', size=128),
        'group_ids': fields.one2many('event.registration', 'friendship_id', 'Troops'),
        'addgroup_id' : fields.many2one('event.registration', 'Add Troop', ondelete='set null', domain=[('state','!=', 'cancel')]),
        }
    
    
#     def name_get(self, cr, uid, ids, context=None):
#         if context is None:
#             context = {}
#         if isinstance(ids, (int, long)):
#             ids = [ids]
#         res = []
#         for record in self.browse(cr, uid, ids, context=context):
#             if record.name:
#                 name = record.name + ": "
#             else:
#                 name = "" 
#             for grp in record.group_ids:
#                 name = name + grp.name + "/"
#             name = name[:-1]        
#             res.append((record['id'], name))
#         return res
     
    def onchange_add_group(self, cr, uid, ids, addgroup_id, group_ids, context=None):
        group_ids.append([4,addgroup_id,False])
        print "addgroup", group_ids
        return {'value': {'group_ids': group_ids,
                          'addgroup_id' : None
                          }
                }
dds_camp_area()    
class dds_camp_tshirtsize(osv.osv):
    """ Committee """
    _description = 'T Shirt'
    _name = 'dds_camp.tshirtsize'
    _order = 'sequence, name'
    
    _columns = {
        'name': fields.char('Name', size=64),
        'desc': fields.text('Description'),
        'sizetype' : fields.selection([('tshirt','T-Shirt'),
                                      ('softshell', 'Soft Shell')], "Sizetype"),
        'sequence': fields.integer('Sequence', select=True, help="Gives the sequence order."),        
    }
dds_camp_tshirtsize()

class event_event(osv.osv):
    """ Inherits Event and adds DDS Camp information in the partner form """
    _inherit = 'event.event'
    
    _columns = {
        'webshop_product_nid': fields.integer('Webshop nid'),
        }
    
    def button_open_webevent_url(self, cr, uid, ids, context): 
        """ Open Event
        @return: True
        """
        # logger.info("%s.button_open_drawing_url(): ids = %s", self._name, ids)
        webevent_ref = self.browse(cr, uid, ids)[0].webshop_product_nid
        if webevent_ref:
            return { 'type': 'ir.actions.act_url', 'url': r"%s/node/%s" % (r"http://e2014.gruppe.dds.dk", webevent_ref), 'nodestroy': True, 'target': 'new' }
        return True    

event_event()

class dds_camp_event_participant_day(osv.osv):
    """ Event participant day """
    _description = 'Event participant day'
    _name = 'dds_camp.event.participant.day'
    _order = 'date'
    
    def _calc_day_txt(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for par_day in self.browse(cr, uid, ids, context=context):
            dt = datetime.datetime.strptime(par_day.date, DEFAULT_SERVER_DATE_FORMAT).date()
            res[par_day.id] = {'day_txt' : dt.strftime('%d/%m-%Y')}
        return res
            
    _columns = {
        'participant_id': fields.many2one('dds_camp.event.participant', 'Participant', required=True, select=True, ondelete='cascade'),
        'date' : fields.date('Date'),
        'state': fields.boolean('Participate'),
        'name' : fields.char('Name', size=64),
        'day_txt' : fields.function(_calc_day_txt, type = 'char', size = 32, string='Day', method=True, multi='TXT', store=True),
        'registration_id' : fields.related('participant_id', 'registration_id', type='many2one', relation='event.registration', store=True, string='Group'),
        'age_group' : fields.related('participant_id', 'age_group', type='char', size=16,  store=True, string='Age'),
        'event_id' : fields.related('participant_id', 'registration_id', 'event_id', type='many2one', relation='event.event', store=True, string='Event'), 
        }
    
    def button_reg_confirm(self, cr, uid, ids, context=None, *args):
        return self.write(cr, uid, ids, {'state': True})
             
    def button_reg_cancel(self, cr, uid, ids, context=None, *args):
        return self.write(cr, uid, ids, {'state': False})
dds_camp_event_participant_day()    


class dds_camp_event_participant_agegroup(osv.osv):
    """ Event participants by Age Group """
    _description = 'Event participant by Age Group'
    _name = 'dds_camp.event.agegroup'
    _order = 'age_group'

    def _calc_number(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for ag in self.browse(cr, uid, ids, context=context):
            nbr = 0
            for par in ag.registration_id.participant_ids:
                if par.age_group == ag.age_group:
                    nbr += 1
            res[ag.id] = {'number': nbr}
        return res
                
    _columns = {
        'registration_id': fields.many2one('event.registration', 'Registration', required=True, select=True, ondelete='cascade'),        
        'age_group' : fields.selection([('00-03','Age 0 - 3'),
                                        ('04-05','Age 4 - 5'),
                                         ('06-08','Age 6 - 8'),
                                          ('09-10','Age 9 - 10'),
                                          ('11-12',u'Age 11 - 12'),
                                          ('13-16', 'Age 13 - 16'),
                                          ('17-22', 'Age 17 - 22'),
                                          ('22+','Age 22+ and leaders'),
                                          ('unknown', 'Unknown')],'Age group',required=True),
        'pre_reg' : fields.integer('Number of preregistered'),        
        'number': fields.function(_calc_number, type = 'integer', string='Number of participants', method=True, multi='PART' ),
    }
    
dds_camp_event_participant_agegroup() 
   
class dds_camp_event_participant(osv.osv):
    """ Event participants """
    _description = 'Event participant'
    _name = 'dds_camp.event.participant'
    _order = 'name'
    _inherit = 'mail.thread'
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        print "fields_view_get entry:", view_id, toolbar
        res = super(dds_camp_event_participant, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type,
                                                                    context=context, toolbar=toolbar, submenu=submenu)
        
        print "FORM: ", res['name'] 
        if res['name'] == u'portal.registration.participant.form' or res['name'] == u'portal.dds_camp.staff.form':
            #print "Form found!"
            #print "Context: ", context
#             reg_id = context.get('active_id', False)
#             
#             if reg_id:
#                 reg = self.pool.get('event.registration').browse(cr, uid, [reg_id])[0]
#                 from_date = datetime.datetime.strptime(reg.event_id.date_begin, DEFAULT_SERVER_DATETIME_FORMAT).date()
#                 to_date = datetime.datetime.strptime(reg.event_id.date_end, DEFAULT_SERVER_DATETIME_FORMAT).date()  
#                 print "dates", from_date, to_date
#             if not reg_id:
            event = self.pool.get('event.event').browse(cr, uid, [1])[0]
            from_date = datetime.datetime.strptime(event.date_begin, DEFAULT_SERVER_DATETIME_FORMAT).date()
            to_date = datetime.datetime.strptime(event.date_end, DEFAULT_SERVER_DATETIME_FORMAT).date()  
            print "dates", from_date, to_date
            
            if from_date:
                dt = from_date
                delta = datetime.timedelta(days=1)
                while dt <= to_date:
                    res['fields'][dt.strftime('date_%Y_%m_%d')] = {'selectable': True, 'type': 'boolean', 'string': dt.strftime('%d/%m-%Y'), 'views': {}}
                    dt += delta
                print res['arch']
                doc = ET.XML(res['arch'])
                #print "FindAll:",".//group[@string='"+ _('Camp Period') +"']"
                for grp in doc.findall(".//group[@string='Camp Period']"):
                    dt = from_date
                    while dt <= to_date:
                        fld = ET.SubElement(grp, 'field', {'name': dt.strftime('date_%Y_%m_%d')})
                        setup_modifiers(fld, res['fields'][dt.strftime('date_%Y_%m_%d')])
                        dt += delta
                for grp in doc.findall(".//group[@string='Lejrperiode']"):
                    dt = from_date
                    while dt <= to_date:
                        fld = ET.SubElement(grp, 'field', {'name': dt.strftime('date_%Y_%m_%d')})
                        setup_modifiers(fld, res['fields'][dt.strftime('date_%Y_%m_%d')])
                        dt += delta        
                # Staff camps
                for grp in doc.findall(".//group[@string='Teknik forlejr']"):
                    dt = datetime.datetime.strptime('2014-07-12', '%Y-%m-%d').date()
                    to_date = datetime.datetime.strptime('2014-07-17', '%Y-%m-%d').date()
                    while dt <= to_date:
                        res['fields'][dt.strftime('date_%Y_%m_%d')] = {'selectable': True, 'type': 'boolean', 'string': dt.strftime('%d/%m-%Y'), 'views': {}}
                        fld = ET.SubElement(grp, 'field', {'name': dt.strftime('date_%Y_%m_%d')})
                        setup_modifiers(fld, res['fields'][dt.strftime('date_%Y_%m_%d')])
                        dt += delta           
                
                for grp in doc.findall(".//group[@string='Forlejr']"):
                    dt = datetime.datetime.strptime('2014-07-18', '%Y-%m-%d').date()
                    to_date = datetime.datetime.strptime('2014-07-21', '%Y-%m-%d').date()
                    while dt <= to_date:
                        res['fields'][dt.strftime('date_%Y_%m_%d')] = {'selectable': True, 'type': 'boolean', 'string': dt.strftime('%d/%m-%Y'), 'views': {}}
                        fld = ET.SubElement(grp, 'field', {'name': dt.strftime('date_%Y_%m_%d')})
                        setup_modifiers(fld, res['fields'][dt.strftime('date_%Y_%m_%d')])
                        dt += delta
                
                for grp in doc.findall(".//group[@string='Efterlejr']"):
                    dt = datetime.datetime.strptime('2014-08-01', '%Y-%m-%d').date()
                    to_date = datetime.datetime.strptime('2014-08-03', '%Y-%m-%d').date()
                    while dt <= to_date:
                        res['fields'][dt.strftime('date_%Y_%m_%d')] = {'selectable': True, 'type': 'boolean', 'string': dt.strftime('%d/%m-%Y'), 'views': {}}
                        fld = ET.SubElement(grp, 'field', {'name': dt.strftime('date_%Y_%m_%d')})
                        setup_modifiers(fld, res['fields'][dt.strftime('date_%Y_%m_%d')])
                        dt += delta     
                print ET.tostring(doc)              
                res['arch'] = ET.tostring(doc) 
        return res

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        if 'days_ids' not in fields:
            fields.append('days_ids')
        res = super(dds_camp_event_participant, self).read(cr, uid, ids, fields, context=context, load=load)
        for r in res:
            if r.has_key('days_ids'):
                for d in self.pool.get('dds_camp.event.participant.day').browse(cr, uid, r['days_ids'], context):
                    r.update({ 'date_' + d.date.replace('-','_') : d.state})
        return res

    def write(self, cr, uid, ids, values, context=None):
        
        day_obj = self.pool.get('dds_camp.event.participant.day')
        for participant in self.browse(cr, uid, ids):
            if participant.days_ids:
                for d in participant.days_ids:
                    if values.has_key('date_' + d.date.replace('-','_')):
                        day_obj.write(cr, SUPERUSER_ID, [d.id], {'state' : values['date_' + d.date.replace('-','_')]})
                        del values['date_' + d.date.replace('-','_')]    
            else:
                from_date = datetime.datetime.strptime(participant.registration_id.event_id.date_begin, DEFAULT_SERVER_DATETIME_FORMAT).date()
                to_date = datetime.datetime.strptime(participant.registration_id.event_id.date_end, DEFAULT_SERVER_DATETIME_FORMAT).date()  
                print "dates", from_date, to_date
                dt = from_date
                delta = datetime.timedelta(days=1)
                while dt <= to_date:
                    if values.has_key(dt.strftime('date_%Y_%m_%d')):
                        day_obj.create(cr, SUPERUSER_ID, {'participant_id' : participant.id,
                                                          'date' : dt,
                                                          'state': values[dt.strftime('date_%Y_%m_%d')]})
                        del values['date_' + d.date.replace('-','_')]
                    else:
                        day_obj.create(cr, SUPERUSER_ID, {'participant_id' : participant.id,
                                                          'date' : dt,
                                                          'state': False})    
                    dt += delta
        
        for k in values.keys():
            if k[:5] == 'date_':
                del values[k]
                
        res = super(dds_camp_event_participant, self).write(cr, uid, ids, values, context)
        return res
    
    def create(self, cr, uid, values, context=None):
        id = super(dds_camp_event_participant, self).create(cr, uid, values, context)
        day_obj = self.pool.get('dds_camp.event.participant.day')
        for participant in self.browse(cr, uid, [id]):
            from_date = datetime.datetime.strptime(participant.registration_id.event_id.date_begin, DEFAULT_SERVER_DATETIME_FORMAT).date()
            to_date = datetime.datetime.strptime(participant.registration_id.event_id.date_end, DEFAULT_SERVER_DATETIME_FORMAT).date()  
            dt = from_date
            delta = datetime.timedelta(days=1)
            while dt <= to_date:
                if values.has_key(dt.strftime('date_%Y_%m_%d')):
                    day_obj.create(cr, SUPERUSER_ID, {'participant_id' : participant.id,
                                                      'date' : dt,
                                                      'state': values[dt.strftime('date_%Y_%m_%d')]})
                else:
                    day_obj.create(cr, SUPERUSER_ID, {'participant_id' : participant.id,
                                                      'date' : dt,
                                                      'state': False})    
                dt += delta
        return id 

    def fields_get(self, cr, uid, allfields=None, context=None, write_access=True):
        res = super(dds_camp_event_participant, self).fields_get(cr, uid, allfields, context, write_access)
         
#         res['date_2014_07_22'] = {
#                         'type': 'boolean',
#                         'string': '22/7-2014',
#                         'help': 'Tirsdag',
#                         'exportable': False,
#                     }
        return res
        
    def _calc_summery(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for par in self.browse(cr, uid, ids, context=context):
            dates= []
            fee = 0
            text = ''
            age = 15 # Default to pay age
            full = True
            for d in par.days_ids:
                if d.state:
                    dates.append(d.date)
                else:
                    full = False
            if full:
                res[par.id] = {'day_summery' : _('Full periode')}
            else:
                dates.sort()
                for d in dates:
                    text += ',' + d[8:]
                res[par.id] = {'day_summery' : text[1:]}
            if par.leader:
                ag = '22+'
            else:             
                age = self._age(par.birth, '2014-07-22')
                ag = 'unknown'
                if age:
                    if age <= 3:
                        ag = '00-03'
                    if age >= 4 and age <= 5:
                        ag = '04-05'
                    if age >= 6 and age <= 8:
                        ag = '06-08'
                    if age >= 9 and age <= 10:
                        ag = '09-10'
                    if age >= 11 and age <= 12:
                        ag = '11-12'
                    if age >= 13 and age <= 16:
                        ag = '13-16'
                    if age >= 17 and age <= 22:
                        ag = '17-22'
                    if age > 22:
                        ag = '22+'
            if age > 3 or not age:
                if full:
                    fee = 1500.00
                elif text == ',25,26,27':    # Special pris for weekenden fredag – søndag 500 kr
                    fee = 500.00
                elif text == ',22,23,24,25,26,27':               # Tirsdag til Søndag 6 dage 1.050 kr
                    fee = 1050.00
                elif text == ',27,28,29,30,31':               # Søndag til Torsdag 5 dage 850 kr.
                    fee = 850.00
                elif text == ',26,27,28,29,30,31':               # Lørdag til Torsdag 6 dage 1.050 kr.
                    fee = 1050.00    
                elif len(dates) > 7:                # Ved deltagelse i 8 dage eller mere betales der fuld pris 1.500 kr. 
                    fee = 1500.00
                         
            res[par.id].update({'age_group': ag,
                                'camp_fee': fee})
        return res
    
    def _age(self, date_of_birth_str, date_begin_str):
        if date_of_birth_str:
            date_of_birth = datetime.datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
            date_begin = datetime.datetime.strptime(date_begin_str, '%Y-%m-%d').date()
            if date_of_birth >= date_begin.replace(year = date_of_birth.year):
                return date_begin.year - date_of_birth.year - 1
            else:
                return date_begin.year - date_of_birth.year
        else:
            return False
    
    def onchange_birth(self, cr, uid, ids, birth, context=None):
        age = self._age(birth, '2014-07-22')
        ag = False
        if age >= 6 and age <= 8:
            ag = '06-08'
        if age >= 9 and age <= 10:
            ag = '09-10'
        if age >= 11 and age <= 12:
            ag = '11-12'
        if age >= 13 and age <= 16:
            ag = '13-16'
        if age >= 17 and age <= 22:
            ag = '17-22'
        if age > 22:
            ag = '22+'
            
        res = {'values' : {'age_group': ag}}    
        return res
    
    def onchange_state(self, cr, uid, ids, state_id, context=None):
        if state_id:
            country_id=self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id
            return {'value':{'country_id':country_id}}
        return {}
    
    def onchange_zip_id(self, cursor, uid, ids, zip_id, context=None):
        if not zip_id:
            return {}
        if isinstance(zip_id, list):
            zip_id = zip_id[0]
        bzip = self.pool['res.better.zip'].browse(cursor, uid, zip_id, context=context)
        return {'value': {'zip': bzip.name,
                          'city': bzip.city,
                          'country_id': bzip.country_id.id if bzip.country_id else False,
                          'state_id': bzip.state_id.id if bzip.state_id else False,
                          'zip_id': False 
                          }
                }

    
    def _get_pars_from_days(self, cr, uid, days_ids, context=None):
        days = self.pool.get('dds_camp.event.participant.day').browse(cr, uid, days_ids, context=context)
        print '_get_pars_from_days', days
        par_ids = [day.participant_id.id for day in days if day.participant_id]
        return par_ids
    
    
            
    _columns = {
        'registration_id': fields.many2one('event.registration', 'Registration', required=True, select=True, ondelete='cascade'),
        'partner_id': fields.many2one('res.partner', 'Participant'),  
        # The following fields are synced to res_partner on Write      
        'name': fields.char('Name', size=128, required=True, select=True),
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip_id': fields.many2one('res.better.zip', 'City/Location'),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state_id': fields.many2one("res.country.state", 'State'),
        'country_id': fields.many2one('res.country', 'Country'),
        'email': fields.char('Email', size=240),
        'phone': fields.char('Phone', size=64),
        # end of res_partner fields
        
        'rel_phone': fields.char('Relatives phonenumber', size=64),
        'birth' : fields.date('Birth date'),

        'patrol' : fields.char('Patrol name', size=64),
        'appr_leader' : fields.boolean('Leder godkendt', track_visibility='onchange'),
        'leader' : fields.boolean('Is Leader'),
        'days_ids': fields.one2many('dds_camp.event.participant.day', 'participant_id', 'Participation'),
        'day_summery': fields.function(_calc_summery, type = 'char', size=64, string='Summery', method=True, multi='PART'), 
                                       #store = {'dds_camp_event_participant_day' : (_get_pars_from_days,['state'],10)}),
        'age_group' : fields.function(_calc_summery, type = 'char', size=16, string='Age group', method=True, multi='PART',store=True),
        'camp_fee' : fields.function(_calc_summery, type = 'float', string='Camp fee', method=True, multi='PART'),                               
#         'age_group' : fields.selection([('06-08','Age 6 - 8'),
#                                           ('09-10','Age 9 - 10'),
#                                           ('11-12',u'Age 11 - 12'),
#                                           ('13-16', 'Age 13 - 16'),
#                                           ('17-22', 'Age 17 - 22'),
#                                           ('22+','Age 22+ and leaders')],'Age group'),
         'memberno' : fields.char('DDS Medlemsnummer', size=32),
         'imported_bm' : fields.boolean(u'Imported from Blåt Medlem'),
         'event_id' : fields.related('registration_id', 'event_id', type='many2one', relation='event.event', store=True, string='Event'),
         'event_id2' : fields.related('registration_id', 'event_id','id', type='integer', string='Event'),   
         
         # Staff registraring
         'workwish' : fields.char('Want to work with', size=64),   
         'committee_id' : fields.many2one('dds_camp.committee', 'Have agreement with committee', track_visibility='onchange', ondelete='set null'),
         'state': fields.selection([('draft','Received'),
                                        ('sent','Sent to committee'),
                                        ('approved','Approved by the committee'),
                                        ('rejected', 'Rejected')],'Approval Procedure', track_visibility='onchange'),
         #'withgroup' : fields.boolean('Also participating with my group'),
         #'group_id' : fields.many2one('event.registration', 'Group', domain = "[('event_id2','=',1)]"),
         'profession': fields.char('Profession', size=64, help='What do you do for living'),
         'tshirt_size_id' : fields.many2one('dds_camp.tshirtsize', 'Size of T-shirt',domain = "[('sizetype','=','tshirt')]"),
         'softshell_size_id' : fields.many2one('dds_camp.tshirtsize', u'Bestilling af Soft shell jakke pris 400 kr - størrelse', domain = "[('sizetype','=','softshell')]"),
         'drvlic_car' : fields.boolean('Car'),
         'drvlic_truck' : fields.boolean('Truck'),
         'drvlic_bus' : fields.boolean('Bus'),
         'drvlic_trailer' : fields.boolean('Trailer'),
         'drvlic_tractor' : fields.boolean('Tractor'),
         'drvlic_flift' : fields.boolean('Forklift'),
         'drvlic_other' : fields.boolean('Other'),
         'functitle' : fields.selection([('fm','Formand'),
                                        ('um','Udvalgsmedlem'),
                                        ('hlp',u'Hjælper'),
                                        ('chld','Hjælperbarn'),
                                        ('rel',u'Pårørende'),
                                        ('ex', 'Ekstern (ikke betalende)'),
                                        ('lc','Lejrchef'),
                                        ('kon', 'Konsulent')],'Function'),
         'partype' : fields.selection([('',''), ('itshead', 'ITS Head'),('other', 'ITS Other')], 'Record Type'),
         'is_relative' : fields.boolean(u'Deltager som pårørende'),       
         'staff_id': fields.many2one('dds_camp.staff', 'Tilmeldt under', select=True, ondelete='cascade'),
    }
    
    #_sql_constraints = [
    #    ('participation_uniq', 'unique(registration_id, partner_id)', 'Participant must be unique!'),
    #]
    
    _defaults = {'event_id2' : lambda *a: 1}
    
    def button_confirm(self, cr, uid, ids, context=None):
        
        template = False
        template = self.pool.get('ir.model.data').get_object(cr, uid, 'dds_camp', 'new_ist_member')
        assert template._name == 'email.template'
        
        for par in self.browse(cr, uid, ids, context):
            print "Confirm", template.id, par.id, par._name, par.name
            self.pool.get('email.template').send_mail(cr, uid, template.id, par.id, force_send=True, raise_exception=True, context=context)
         
        return self.write(cr, uid, ids, {'state': 'sent'}, context=context)

    def button_approve(self, cr, uid, ids, context=None):
        for par in self.browse(cr, uid, ids, context):
            self.pool.get('email.template').send_mail(cr, uid, par.committee_id.template_id.id, par.id, force_send=True, raise_exception=True, context=context)
        
        return self.write(cr, uid, ids, {'state': 'approved'}, context=context)
    
    def button_reject(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'rejected'}, context=context)
        
    def action_select_all_days(self, cr, uid, ids, context):
       
        res = {}
        values = {}
        for participant in self.browse(cr, uid, ids):
            from_date = datetime.datetime.strptime(participant.registration_id.event_id.date_begin, DEFAULT_SERVER_DATETIME_FORMAT).date()
            to_date = datetime.datetime.strptime(participant.registration_id.event_id.date_end, DEFAULT_SERVER_DATETIME_FORMAT).date()  
            dt = from_date
            delta = datetime.timedelta(days=1)
            while dt <= to_date:
                values[dt.strftime('date_%Y_%m_%d')] = True
                dt += delta
        
        res['value'] = values
        print res
        return res
        
    def create_day_lines(self, cr, uid, ids, from_dt, to_dt, context):
        day_obj = self.pool.get('dds_camp.event.participant.day')
        participant = self.browse(cr, uid, ids)[0]
               
        if participant.days_ids:
                day_obj.write(cr, SUPERUSER_ID, [day.id for day in participant.days_ids if day.date >= from_dt and day.date <= to_dt], {'state' : True})    
        else:
            from_date = datetime.datetime.strptime(from_dt, DEFAULT_SERVER_DATE_FORMAT).date()
            to_date = datetime.datetime.strptime(to_dt, DEFAULT_SERVER_DATE_FORMAT).date()  
            print "dates", from_date, to_date
            dt = from_date
            delta = datetime.timedelta(days=1)
            while dt <= to_date:
                day_obj.create(cr, SUPERUSER_ID, {'participant_id' : participant.id,
                                             'date' : dt,
                                             'state': True})
                dt += delta    
    
    def get_parcipant_form(self, cr, uid, ids, context):
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'dds_camp', 'portal_view_event_registration_participant_create')
        view_id = view_ref and view_ref[1] or False,
        return {
               'type': 'ir.actions.act_window',
               'name': _('Add Participant'),
               'view_mode': 'form',
               'view_type': 'form',
               'view_id': view_id,
               #'views': [(False, 'form')],
               'res_model': 'dds_camp.event.participant',
               'res_id' : ids[0],
               'nodestroy': True,
               'target':'new',
               'context': context,
               }
        
    def action_create_day_teknik(self, cr, uid, ids, context):
        self.create_day_lines(cr, uid, ids, '2014-07-12', '2014-07-17', context)
        
    
    def action_create_day_teknik2(self, cr, uid, ids, context):
        self.create_day_lines(cr, uid, ids, '2014-07-12', '2014-07-17', context)
        return self.get_parcipant_form(cr, uid, ids, context) 
        
    def action_create_day_precamp(self, cr, uid, ids, context):
        self.create_day_lines(cr, uid, ids, '2014-07-18', '2014-07-21', context)
        
    def action_create_day_precamp2(self, cr, uid, ids, context):
        self.create_day_lines(cr, uid, ids, '2014-07-18', '2014-07-21', context)
        return self.get_parcipant_form(cr, uid, ids, context)
    
    def action_create_day_maincamp(self, cr, uid, ids, context):
        self.create_day_lines(cr, uid, ids, '2014-07-22', '2014-07-31', context)        
    
    def action_create_day_maincamp2(self, cr, uid, ids, context):
        self.create_day_lines(cr, uid, ids, '2014-07-22', '2014-07-31', context)        
        return self.get_parcipant_form(cr, uid, ids, context)
    
    def action_create_day_postcamp(self, cr, uid, ids, context):
        self.create_day_lines(cr, uid, ids, '2014-08-01', '2014-08-03', context)        
    
    def action_create_day_postcamp2(self, cr, uid, ids, context):
        self.create_day_lines(cr, uid, ids, '2014-08-01', '2014-08-03', context)        
        return self.get_parcipant_form(cr, uid, ids, context)
    
    def action_create_day_lines2(self, cr, uid, ids, context):
        self.action_create_day_lines(cr, uid, ids, context)
        return self.get_parcipant_form(cr, uid, ids, context)
    
    def action_create_day_lines(self, cr, uid, ids, context):
        day_obj = self.pool.get('dds_camp.event.participant.day')
        participant = self.browse(cr, uid, ids)[0]
               
        if participant.days_ids:
                day_obj.write(cr, SUPERUSER_ID, [day.id for day in participant.days_ids], {'state' : True})    
        else:
            from_date = datetime.datetime.strptime(participant.registration_id.event_id.date_begin, DEFAULT_SERVER_DATETIME_FORMAT).date()
            to_date = datetime.datetime.strptime(participant.registration_id.event_id.date_end, DEFAULT_SERVER_DATETIME_FORMAT).date()  
            print "dates", from_date, to_date
            dt = from_date
            delta = datetime.timedelta(days=1)
            while dt <= to_date:
                day_obj.create(cr, SUPERUSER_ID, {'participant_id' : participant.id,
                                             'date' : dt,
                                             'state': True})
                dt += delta
    
            
     
    def action_create_day_some(self, cr, uid, ids, context):
        day_obj = self.pool.get('dds_camp.event.participant.day')
        participant = self.browse(cr, uid, ids)[0]
       
        if not participant.days_ids:
            from_date = datetime.datetime.strptime(participant.registration_id.event_id.date_begin, DEFAULT_SERVER_DATETIME_FORMAT).date()
            to_date = datetime.datetime.strptime(participant.registration_id.event_id.date_end, DEFAULT_SERVER_DATETIME_FORMAT).date()  
            print "dates", from_date, to_date
            dt = from_date
            delta = datetime.timedelta(days=1)
            while dt <= to_date:
                day_obj.create(cr, SUPERUSER_ID, {'participant_id' : participant.id,
                                         'date' : dt,
                                         'state': False})
                dt += delta
    
    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        partner_obj = self.pool.get('res.partner')
        partner = partner_obj.browse(cr, uid, [partner_id])[0]
        res = {}
        values = {}
        for k in ['name', 'street', 'street2', 'email','phone']:
            values.update({k : getattr(partner, k)})
        values.update({'state_id' : partner.state_id.id,
                       'country_id' : partner.country_id.id})
        res['value'] = values
        print res
        return res
    
#     def write(self, cr, uid, ids, vals, context=None):
#         res = super(dds_camp_event_participant, self).write(cr, uid, ids, vals, context=context)
#         partner_obj = self.pool.get('res.partner')
#         print "write", ids, vals 
#         values = {}
#         for k in ['name', 'street', 'street2', 'state_id', 'country_id', 'email','phone']:
#             if vals.has_key(k):    
#                 values.update({k : vals[k]})
#             if vals.has_key('partner_id'):
#                 partner_obj.write(cr,uid,[vals['partner_id']], values, context)
#                 print "write", values
#             else:
#                 #values.update({'parent_id' : par.registration_id.partner_id.id})
#                 partner_id = partner_obj.create(cr,uid, values, context)
#                 self.write(cr, uid, {'partner_id': partner_id}, context)
#                 print "create", partner_id, values            
#         return res
        
        # override list in custom module to add/drop columns or change order
    def _report_xls_fields(self, cr, uid, context=None):
        return [
            'name', 'birth', 'street', 'street2','zip','city','day_summery'
            #'journal', 'period', 'partner', 'account',
            #'date_maturity', 'debit', 'credit', 'balance',
            #'reconcile', 'reconcile_partial', 'analytic_account',
            #'ref', 'partner_ref', 'tax_code', 'tax_amount', 'amount_residual',
            #'amount_currency', 'currency_name', 'company_currency',
            #'amount_residual_currency',
            #'product', 'product_ref', 'product_uom', 'quantity',
            #'statement', 'invoice', 'narration', 'blocked',
        ]

    # Change/Add Template entries
    def _report_xls_template(self, cr, uid, context=None):
        """
        Template updates, e.g.

        my_change = {
            'move':{
                'header': [1, 20, 'text', _('My Move Title')],
                'lines': [1, 0, 'text', _render("line.move_id.name or ''")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}
               
dds_camp_event_participant()
    
class event_registration(osv.osv):
    """ Inherits Event and adds DDS Camp information in the Registration form """
    _inherit = 'event.registration'
    
#     def name_get(self, cr, uid, ids, context=None):
#         if not ids:
#             return []

# 
#         if isinstance(ids, (long, int)):
#             ids = [ids]
# 
#         res = []
#         for record in self.browse(cr, uid, ids, context=context):
#             display_name = record.name + ' (' + (record.event_id.name or '') + ')'
#             res.append((record['id'], display_name))
#         return res
#     
    def _calc_number(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for reg in self.browse(cr, uid, ids, context=context):
            nbr = 0
            pre = 0
            
            for ag in reg.agegroup_ids:
                nbr = nbr + ag.number
                pre = pre + ag.pre_reg
            
            fee = 0
            for par in reg.participant_ids:
                fee = fee + par.camp_fee
            
            last_login = False
            users = False
            if reg.partner_id:
                for usr in reg.partner_id.user_ids:
                    users = True 
                    if usr.login_date:
                        if last_login:
                            last_login = max(last_login, usr.login_date)
                        else:
                            last_login = usr.login_date 
                if reg.partner_id.child_ids:
                    for child in reg.partner_id.child_ids:
                        if child.user_ids:
                            users = True            
                            for usr in child.user_ids:
                                if usr.login_date:
                                    if last_login:
                                        last_login = max(last_login, usr.login_date)
                                    else:
                                        last_login = usr.login_date                        
            res[reg.id] = {'reg_number': nbr,
                           'pre_reg_number': pre,
                           'camp_fee_tot' : fee,
                           'camp_fee_charged' : max(fee, reg.camp_fee_min),
                           'last_login' : last_login,
                           'user_created' : users}
        return res
            
    _columns = {
        'event_id2' : fields.related('event_id','id', type='integer', string='Event'),
        'webshop_orderno': fields.integer('Webshop Order No'),
        'webshop_order_product_id': fields.integer('Webshop Order Line No'),
        'participant_ids': fields.one2many('dds_camp.event.participant', 'registration_id', 'Registration.'),
        'par_ids': fields.one2many('dds_camp.event.participant', 'registration_id', 'Registration',domain=[('partype','!=','itshead')]),
        'agegroup_ids': fields.one2many('dds_camp.event.agegroup', 'registration_id', 'Age grouping.'),
        
        
        'country_id': fields.many2one('res.country', 'Country'),
        'organization_id': fields.many2one('dds_camp.scout.org', 'Scout Organization'),
        'organization': fields.selection([('dds','Det Danske Spejderkorps'),
                                          ('dbs','Danske Baptisters Spejderkorps'),
                                          ('dgp',u'De Grønne Pigespejdere'),
                                          ('dui', 'DUI Leg og Virke'),
                                          ('fdf', 'FDF'),
                                          ('kfum','KFUM Spejderne'),
                                          ('waggs','WAGGS'),
                                          ('wosm', 'WOSM'),
                                          ('other','Other')],'Scout Organization - OLD'),
        'scout_division' : fields.char('Division/District', size=64),
        'municipality_id': fields.many2one('dds_camp.municipality', 'Municipality', select=True, ondelete='set null'),  
        'ddsgroup': fields.integer('DDS Gruppenr'),     
        'region' : fields.char('Region', size=64),
        
        # Contact
        'contact_partner_id': fields.many2one('res.partner', 'Contact', states={'done': [('readonly', True)]}),
        'contact_email': fields.related('contact_partner_id','email', readonly=True, type='char', relation='res.partner', string='Email'),
#
        
#         'contact_name': fields.char('Contact Name', size=128, required=True, select=True),
#         'contact_street': fields.char('Street', size=128),
#         'contact_street2': fields.char('Street2', size=128),
#         'contact_zip': fields.char('Zip', change_default=True, size=24),
#         'contact_city': fields.char('City', size=128),
#         'contact_state_id': fields.many2one("res.country.state", 'State'),
#         'contact_country_id': fields.many2one('res.country', 'Country'),
#         'contact_email': fields.char('Email', size=240),
#         'contact_phone': fields.char('Phone', size=64),
#         
        # Economic Contact
        'econ_partner_id': fields.many2one('res.partner', 'Economic Contact', states={'done': [('readonly', True)]}),
        'econ_email': fields.related('econ_partner_id','email', readonly=True, type='char', relation='res.partner', string='Email'),
#         
#         'econ_name': fields.char('Economic Contact Name', size=128, required=True, select=True),
#         'econ_street': fields.char('Street', size=128),
#         'econ_street2': fields.char('Street2', size=128),
#         'econ_zip': fields.char('Zip', change_default=True, size=24),
#         'econ_city': fields.char('City', size=128),
#         'econ_state_id': fields.many2one("res.country.state", 'State'),
#         'econ_country_id': fields.many2one('res.country', 'Country'),
#         'econ_email': fields.char('Email', size=240),
#         'econ_phone': fields.char('Phone', size=64),
        'foreigners' : fields.boolean('Foreigners'),
        'signed_up' : fields.boolean('Signed up'),
        'shared_transport': fields.selection([('yes','Yes'),
                                              ('no', 'No'),
                                              ('maybe','Maybe')],'Shared transport'),
                
        # Home Hsopitality
        'hh_precamp' : fields.boolean('Would like home hospitality before the camp'),
        'hh_aftercamp' : fields.boolean('Would like home hospitality after the camp'),
        'hh_precamp_prv' : fields.boolean('Can provide home hospitality before the camp'),
        'hh_aftercamp_prv' : fields.boolean('Can provide home hospitality after the camp'),
        'want_friendshipgroup': fields.boolean('Want a friendship group'),
        'has_friendshipgroup' : fields.boolean('Do you have a friendship group participate in the camp'),
        'friendshipgroup_name' : fields.char('Name of friendship group'),

        'hcap' : fields.boolean('Do you bring any handicapped scouts'),
        'hcap_desc': fields.text('Describe the handicap'),
        'hcap_specneeds' : fields.text('Describe special needs'),
        'food_allergy' : fields.boolean('Do you have any allergy sufferer'),
        'food_allergy_desc': fields.text('Describe the allergy'),
        
        #Internal fields
        'agreements': fields.text('What have been arranged'),
        'internal_note' : fields.text('Internal note'),
        'reg_number': fields.function(_calc_number, type = 'integer', string='# Participants', method=True, multi='PART' ),
        'pre_reg_number': fields.function(_calc_number, type = 'integer', string='# Pre-registred', method=True, multi='PART' ),
        'camp_fee_min' : fields.float('Minimum Camp Fee'),
        'camp_fee_tot': fields.function(_calc_number, type = 'float', string='Camp Fee Total', method=True, multi='PART' ),
        'camp_fee_charged' : fields.function(_calc_number, type = 'float', string='Camp Fee Charged', method=True, multi='PART' ),
        'last_login' : fields.function(_calc_number, type = 'date', string='Last Login Date', method=True, multi='PART' ),
        'user_created' : fields.function(_calc_number, type = 'boolean', string='Users created', method=True, multi='PART' ),
        
        # Staff registraring
        'accommodation' : fields.selection([('tents','Tents'),
                                          ('caravan','Caravan'),
                                          ('camplet',u'CampLet'),
                                          ('cottent', 'Cottage tent'),
						('camper', 'Camper'),
                                          ('group', 'By my Troop'),
                                          ('otherstaff','At other Staff'),
                                          ('other','Outside Camp')],'Accomadation'),
        'tent_nb' : fields.integer('Number of tents'),        
        'parking' : fields.boolean('Do you need parking?'),
        'power' : fields.boolean('Do you need 230 V power - for a fee 50 kr.'),
        'camparea_id' : fields.many2one('dds_camp.area', 'Camp Area', ondelete='set null'),
        'friendship_id' : fields.many2one('dds_camp.friendship', 'Friendship Grouping', ondelete='set null'), 
        'entry_dk': fields.char('Entry point in Denmark', 128),
        'exit_dk': fields.char('Exit point in Denmark', 128),       
    }
    
    def write(self, cr, uid, ids, values, context=None):
        res = super(event_registration, self).write(cr, uid, ids, values, context)
        
        ag_obj = self.pool.get('dds_camp.event.agegroup')
        for e in self.browse(cr, uid, ids, context):
            if len(e.agegroup_ids) < 9:
                ag = []
                for a in e.agegroup_ids:
                    ag.append(a.age_group)
                for a in ['00-03','04-05','06-08','09-10','11-12','13-16','17-22','22+','unknown']:
                    if a not in ag:
                        ag_obj.create(cr, SUPERUSER_ID, {'registration_id' : e.id,
                                                         'age_group' : a,
                                                         'pre_reg' : 0}
                                                         )
                            
        
        return res
    
    def message_get_suggested_recipients(self, cr, uid, ids, context=None):
        recipients = super(event_registration, self).message_get_suggested_recipients(cr, uid, ids, context=context)
        try:
            for reg in self.browse(cr, uid, ids, context=context):
                if reg.partner_id:
                    self._message_add_suggested_recipient(cr, uid, recipients, reg, partner=reg.partner_id, reason=_('Group'))
                if reg.contact_partner_id:
                    self._message_add_suggested_recipient(cr, uid, recipients, reg, partner=reg.contact_partner_id, reason=_('Group Contact'))
                if reg.econ_partner_id:
                    self._message_add_suggested_recipient(cr, uid, recipients, reg, partner=reg.econ_partner_id, reason=_('Group Econ. Contact'))
                if reg.email:
                    self._message_add_suggested_recipient(cr, uid, recipients, reg, email=reg.email, reason=_('Registration Email'))
        except (osv.except_osv, orm.except_orm):  # no read access rights -> just ignore suggested recipients because this imply modifying followers
            pass
        return recipients
        
    def onchange_country_id(self, cr, uid, ids, country_id, context=None):       
                
        res = {}           
        # - set a domain on organization_id
        res['domain'] = {'organization_id': [('country_id','=',country_id)]}      
        return res
    
    def onchange_ddsgroup(self, cr, uid, ids, ddsgroup, partner_id, econ_partner_id, context=None):
         
        res = {}
         
        if ddsgroup > 0:
            res['value'] = {}
            
            ir_config_parameter = self.pool.get("ir.config_parameter")
            params = eval(ir_config_parameter.get_param(cr, uid, "dds_camp.bm_settings", context=context))
            partner_obj = self.pool.get('res.partner')
            
            #Get Group info
            params.update({'action' : 'organizations',
                           'org' : ddsgroup})
            rows = ET.parse(urlopen('%(url)s%(action)s?system=%(system)s&password=%(password)s&org=%(org)s' % params))
            for row in rows.getroot():
                org = dict((e.tag, e.text) for e in row)
                # Create/update Partner
                
                if org.has_key('organizationKommune'):
                    muni = self.pool.get('dds_camp.municipality')
                    muni_ids = muni.search(cr, uid, [('number', '=', int(org['organizationKommune']))])
                else:
                    muni_ids = False    
                res['value'].update({'name': org['docTitle'],
                                     'country_id' : 60, #Denmark
                                     'organization_id' : 1843, #DDS
                                     'scout_division' : org['organizationDivisionName'] if org.has_key('organizationDivisionName') else False,
                                     'email' : org['organizationEMail'] if org.has_key('organizationEMail') else False,
                                     'municipality_id' : muni_ids[0] if muni_ids else False,
                                     })
                partner = {}
                for k,v in partmap:
                    if org.has_key(k):
                        partner[v] = org[k]
                        
                if partner_id:
                    partner_obj.write(cr, uid, [partner_id], partner, context)
                else:
                    partner['is_company'] = True
                    partner_id = partner_obj.create(cr, uid, partner, context)
                        
                #only process first row..
                break
                
            #Get kasserer info
            #1: Find by Trust Code
            params.update({'action': 'memberships',
                           'trustcodes': '66' })
            
            print 'URL: ', '%(url)s%(action)s?system=%(system)s&password=%(password)s&org=%(org)s&trustcodes=%(trustcodes)s' % params
            rows = ET.parse(urlopen('%(url)s%(action)s?system=%(system)s&password=%(password)s&org=%(org)s&trustcodes=%(trustcodes)s' % params))
            for row in rows.getroot():
                membership = dict((e.tag, e.text) for e in row)
                if membership:
                    print membership
                    #fetch memberdata
                    params.update({'action': 'members',
                                   'memberNumber': membership['memberNumber']})
                    rows2 = ET.parse(urlopen('%(url)s%(action)s?system=%(system)s&password=%(password)s&org=%(org)s&memberNumber=%(memberNumber)s' % params))
                    for row2 in rows2.getroot():
                        member = dict((e.tag, e.text) for e in row2)
                        # Create/update Econ Partner
                        econ = {}
                        for k,v in econmap:
                            if member.has_key(k):
                                econ[v] = member[k]
                        
                        if member.has_key('userLastname'):
                            econ['name'] += ' ' + member['userLastname']
                        
                        econ['zip'] = member['PostalCity'][:4] if member.has_key('PostalCity') and member['PostalCity'] else False  # # zip,
                        econ['city'] =  member['PostalCity'][5:] if member.has_key('PostalCity') and member['PostalCity'] else False  # # city
                        econ['country_id'] = 60
                        
                        if econ_partner_id:
                            partner_obj.write(cr, uid, [econ_partner_id], econ, context)
                        else:
                            econ['parent_id'] = partner_id
                            econ['is_company'] = False 
                            econ_partner_id = partner_obj.create(cr, uid, econ, context)
                
                res['value'].update({'partner_id' : partner_id,
                                     'econ_partner_id': econ_partner_id
                                     })
            return res 

    def button_open_weborder_url(self, cr, uid, ids, context): 
        """ Open Pre Registretion
        @return: True
        """
        # logger.info("%s.button_open_drawing_url(): ids = %s", self._name, ids)
        weborder_ref = self.browse(cr, uid, ids)[0].webshop_orderno
        if weborder_ref:
            return { 'type': 'ir.actions.act_url', 'url': r"%s/dds/tilmelding/orders/%s/invoice" % (r"http://e2014.gruppe.dds.dk", weborder_ref), 'nodestroy': True, 'target': 'new' }

        return True

    def button_unlink_camparea(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'camparea_id': None})
        
    def button_unlink_friendship(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'friendship_id': None})
        
    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name', 'camparea_id', 'friendship_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if context:
                if context.get('show_camparea', False) and record['camparea_id']:
                    name = name + ' (' + record['camparea_id'][1] + ')'
                if context.get('show_friendship', False) and record['friendship_id']:
                    name = name + ' (' + record['friendship_id'][1] + ')'    
            res.append((record['id'], name))
        return res
    
event_registration()

class dds_staff(osv.osv):
    _name = "dds_camp.staff"
    _description = "Staff signup"
    _inherit = 'mail.thread'
    _inherits = {'event.registration': "reg_id",
                 'dds_camp.event.participant': "par_id"}
    
    _defaults = {'user_id' : lambda self,cr,uid,context: uid,
                 'event_id' : lambda *a: 2}
    
#     def _get_lines(self, cr, uid, ids, field_name, arg, context):
#         res = {}
#         for staff in self.browse(cr, uid, ids, context=context):
#             list_ids = []
#             link = []
#             for par in staff.participant_ids:
#                 if par.id != staff.par_id.id:
#                     list_ids.append(par.id)
#                     link.append((1,par.id,{}))
#                     
#             res[staff.id] = {'view_line_ids': list_ids}
#             #self.write(cr, uid, [staff.id], {'par_ids': link})
#         print res
#         return res   
    
#     def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
#         res = super(dds_staff, self).read(cr, uid, ids, fields, context=context, load=load)
#         self._get_lines(cr, uid, ids, 'view_line_ids', None, context)
#         return res
#                 
    #_columns = {'par_ids': fields.one2many('dds_camp.event.participant', 'registration_id', 'Registration',domain=[('partype','!=','itshead')]),}
    
    _columns = { #'view_line_ids': fields.function(_get_lines, 'Deltager', relation="dds_camp.event.participant", method=True, type="one2many",  multi='VIEW'),
                'list_ids': fields.one2many('dds_camp.event.participant', 'staff_id', 'Participants'),}
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        print "fields_view_get entry:", view_id, toolbar
        res = super(dds_staff, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type,
                                                                    context=context, toolbar=toolbar, submenu=submenu)
        
        #print "FORM: ", res['name'] 
        if res['name'] == u'portal.registration.participant.form' or res['name'] == u'portal.dds_camp.staff.form':
            #print "Form found!"
            #print "Context: ", context
#             reg_id = context.get('active_id', False)
#             
#             if reg_id:
#                 reg = self.pool.get('event.registration').browse(cr, uid, [reg_id])[0]
#                 from_date = datetime.datetime.strptime(reg.event_id.date_begin, DEFAULT_SERVER_DATETIME_FORMAT).date()
#                 to_date = datetime.datetime.strptime(reg.event_id.date_end, DEFAULT_SERVER_DATETIME_FORMAT).date()  
#                 print "dates", from_date, to_date
#             if not reg_id:
            event = self.pool.get('event.event').browse(cr, uid, [1])[0]
            from_date = datetime.datetime.strptime(event.date_begin, DEFAULT_SERVER_DATETIME_FORMAT).date()
            to_date = datetime.datetime.strptime(event.date_end, DEFAULT_SERVER_DATETIME_FORMAT).date()  
            print "dates", from_date, to_date
            
            if from_date:
                dt = from_date
                delta = datetime.timedelta(days=1)
                while dt <= to_date:
                    res['fields'][dt.strftime('date_%Y_%m_%d')] = {'selectable': True, 'type': 'boolean', 'string': dt.strftime('%d/%m-%Y'), 'views': {}}
                    dt += delta
                print res['arch']
                doc = ET.XML(res['arch'])
                #print "FindAll:",".//group[@string='"+ _('Camp Period') +"']"
                for grp in doc.findall(".//group[@string='Camp Period']"):
                    dt = from_date
                    while dt <= to_date:
                        fld = ET.SubElement(grp, 'field', {'name': dt.strftime('date_%Y_%m_%d')})
                        setup_modifiers(fld, res['fields'][dt.strftime('date_%Y_%m_%d')])
                        dt += delta
                for grp in doc.findall(".//group[@string='Lejrperiode']"):
                    dt = from_date
                    while dt <= to_date:
                        fld = ET.SubElement(grp, 'field', {'name': dt.strftime('date_%Y_%m_%d')})
                        setup_modifiers(fld, res['fields'][dt.strftime('date_%Y_%m_%d')])
                        dt += delta        
                # Staff camps
                for grp in doc.findall(".//group[@string='Teknik forlejr']"):
                    dt = datetime.datetime.strptime('2014-07-12', '%Y-%m-%d').date()
                    to_date = datetime.datetime.strptime('2014-07-17', '%Y-%m-%d').date()
                    while dt <= to_date:
                        res['fields'][dt.strftime('date_%Y_%m_%d')] = {'selectable': True, 'type': 'boolean', 'string': dt.strftime('%d/%m-%Y'), 'views': {}}
                        fld = ET.SubElement(grp, 'field', {'name': dt.strftime('date_%Y_%m_%d')})
                        setup_modifiers(fld, res['fields'][dt.strftime('date_%Y_%m_%d')])
                        dt += delta           
                
                for grp in doc.findall(".//group[@string='Forlejr']"):
                    dt = datetime.datetime.strptime('2014-07-18', '%Y-%m-%d').date()
                    to_date = datetime.datetime.strptime('2014-07-21', '%Y-%m-%d').date()
                    while dt <= to_date:
                        res['fields'][dt.strftime('date_%Y_%m_%d')] = {'selectable': True, 'type': 'boolean', 'string': dt.strftime('%d/%m-%Y'), 'views': {}}
                        fld = ET.SubElement(grp, 'field', {'name': dt.strftime('date_%Y_%m_%d')})
                        setup_modifiers(fld, res['fields'][dt.strftime('date_%Y_%m_%d')])
                        dt += delta
                
                for grp in doc.findall(".//group[@string='Efterlejr']"):
                    dt = datetime.datetime.strptime('2014-08-01', '%Y-%m-%d').date()
                    to_date = datetime.datetime.strptime('2014-08-03', '%Y-%m-%d').date()
                    while dt <= to_date:
                        res['fields'][dt.strftime('date_%Y_%m_%d')] = {'selectable': True, 'type': 'boolean', 'string': dt.strftime('%d/%m-%Y'), 'views': {}}
                        fld = ET.SubElement(grp, 'field', {'name': dt.strftime('date_%Y_%m_%d')})
                        setup_modifiers(fld, res['fields'][dt.strftime('date_%Y_%m_%d')])
                        dt += delta     
                #print ET.tostring(doc)              
                res['arch'] = ET.tostring(doc) 
        return res
    
    def write(self, cr, uid, ids, values, context=None):
        
        day_obj = self.pool.get('dds_camp.event.participant.day')
        for participant in self.browse(cr, uid, ids):
            if participant.days_ids:
                for d in participant.days_ids:
                    if values.has_key('date_' + d.date.replace('-','_')):
                        day_obj.write(cr, SUPERUSER_ID, [d.id], {'state' : values['date_' + d.date.replace('-','_')]})
                        del values['date_' + d.date.replace('-','_')]    
            else:
                from_date = datetime.datetime.strptime(participant.registration_id.event_id.date_begin, DEFAULT_SERVER_DATETIME_FORMAT).date()
                to_date = datetime.datetime.strptime(participant.registration_id.event_id.date_end, DEFAULT_SERVER_DATETIME_FORMAT).date()  
                print "dates", from_date, to_date
                dt = from_date
                delta = datetime.timedelta(days=1)
                while dt <= to_date:
                    if values.has_key(dt.strftime('date_%Y_%m_%d')):
                        day_obj.create(cr, SUPERUSER_ID, {'participant_id' : participant.id,
                                                          'date' : dt,
                                                          'state': values[dt.strftime('date_%Y_%m_%d')]})
                        del values['date_' + d.date.replace('-','_')]
                    else:
                        day_obj.create(cr, SUPERUSER_ID, {'participant_id' : participant.id,
                                                          'date' : dt,
                                                          'state': False})    
                    dt += delta
        
        for k in values.keys():
            if k[:5] == 'date_':
                del values[k]
                
        res = super(dds_staff, self).write(cr, uid, ids, values, context)
        return res
    
    
    def button_confirm(self, cr, uid, ids, context=None):
        
        template = False
        template = self.pool.get('ir.model.data').get_object(cr, uid, 'dds_camp', 'new_ist_member')
        assert template._name == 'email.template'
        
        for par in self.browse(cr, uid, ids, context):
            self.pool.get('email.template').send_mail(cr, uid, template.id, par.par_id.id, force_send=True, raise_exception=True, context=context)
         
        return self.write(cr, uid, ids, {'state': 'sent'}, context=context)

    def button_approve(self, cr, uid, ids, context=None):
        for par in self.browse(cr, uid, ids, context):
            self.pool.get('email.template').send_mail(cr, uid, par.par_id.committee_id.template_id.id, par.par_id.id, force_send=True, raise_exception=True, context=context)
        
        return self.write(cr, uid, ids, {'state': 'approved'}, context=context)
    
    def button_reject(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'rejected'}, context=context)
        
    def button_add_participant(self, cr, uid, ids, context=None):
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'dds_camp', 'portal_view_event_registration_participant_create')
        print "View ID:", view_ref
        view_id = view_ref and view_ref[1] or False,
        this = self.browse(cr, uid, ids, context=context)[0]
        
        par_obj = self.pool.get('dds_camp.event.participant')
        par_id = par_obj.create(cr, uid, {'event_id2': 2, 
                                          'registration_id' : this.reg_id.id, 
                                          'state': 'draft', 
                                          'partype' : 'other', 
                                          'street': this.street, 
                                          'street2': this.street2, 
                                          'zip': this.zip, 
                                          'city': this.city, 
                                          'state_id': this.state_id.id if this.state_id else False, 
                                          'country_id': this.country_id.id if this.country_id else False,
                                          'staff_id' : this.id, 
                                          'partype' : 'other',
                                          'name' : this.name.split(' ')[-1] if this.name else False
                                          })
            
        return {
               'type': 'ir.actions.act_window',
               'name': _('Add Participant'),
               'view_mode': 'form',
               'view_type': 'form',
               'view_id': view_id,
               #'views': [(False, 'form')],
               'res_model': 'dds_camp.event.participant',
               'res_id' : par_id,
               'nodestroy': True,
               'target':'new',
               'context': context,
               }
            
    def create_day_lines(self, cr, uid, ids, from_dt, to_dt, context):
        day_obj = self.pool.get('dds_camp.event.participant.day')
        participant = self.browse(cr, uid, ids)[0]
               
        if participant.days_ids:
                day_obj.write(cr, SUPERUSER_ID, [day.id for day in participant.days_ids if day.date >= from_dt and day.date <= to_dt], {'state' : True})    
        else:
            from_date = datetime.datetime.strptime(from_dt, DEFAULT_SERVER_DATE_FORMAT).date()
            to_date = datetime.datetime.strptime(to_dt, DEFAULT_SERVER_DATE_FORMAT).date()  
            print "dates", from_date, to_date
            dt = from_date
            delta = datetime.timedelta(days=1)
            while dt <= to_date:
                day_obj.create(cr, SUPERUSER_ID, {'participant_id' : participant.id,
                                             'date' : dt,
                                             'state': True})
                dt += delta    
    
    def action_create_day_teknik(self, cr, uid, ids, context):
        self.create_day_lines(cr, uid, ids, '2014-07-12', '2014-07-17', context)
        
    def action_create_day_precamp(self, cr, uid, ids, context):
        self.create_day_lines(cr, uid, ids, '2014-07-18', '2014-07-21', context)
        
    def action_create_day_maincamp(self, cr, uid, ids, context):
        self.create_day_lines(cr, uid, ids, '2014-07-22', '2014-07-31', context)        
    
    def action_create_day_postcamp(self, cr, uid, ids, context):
        self.create_day_lines(cr, uid, ids, '2014-08-01', '2014-08-03', context)        
       
    
    def action_create_day_lines(self, cr, uid, ids, context):
        day_obj = self.pool.get('dds_camp.event.participant.day')
        participant = self.browse(cr, uid, ids)[0]
               
        if participant.days_ids:
                day_obj.write(cr, SUPERUSER_ID, [day.id for day in participant.days_ids], {'state' : True})    
        else:
            from_date = datetime.datetime.strptime(participant.registration_id.event_id.date_begin, DEFAULT_SERVER_DATETIME_FORMAT).date()
            to_date = datetime.datetime.strptime(participant.registration_id.event_id.date_end, DEFAULT_SERVER_DATETIME_FORMAT).date()  
            print "dates", from_date, to_date
            dt = from_date
            delta = datetime.timedelta(days=1)
            while dt <= to_date:
                day_obj.create(cr, SUPERUSER_ID, {'participant_id' : participant.id,
                                             'date' : dt,
                                             'state': True})
                dt += delta
                
    def action_create_login(self, cr, uid, ids, context):
        staff = self.browse(cr, uid, ids)[0]
        
        if staff.user_created:
            return
        
        por_obj = self.pool.get('portal.wizard')
        # Create user
        #print "PArtner", staff.reg_id.partner_id.email, staff.email, staff.reg_id.partner_id.id
        por_id = por_obj.create(cr, SUPERUSER_ID, {'portal_id': 11,
                                                   'user_ids': [(0, 0, {'partner_id': staff.reg_id.partner_id.id, 
                                                                       'email': staff.reg_id.email, 
                                                                       'in_portal': True,
                                                                       'staff_id': staff.id})]
                                                   })
        ctx = context
        ctx = {'mail_template' : 'email_template_15', 'mail_tpl_module': '__export__'}
        if ctx.has_key('default_state'):
            del ctx['default_state']
            
        por_obj.action_apply(cr, SUPERUSER_ID, [por_id], ctx)

    def onchange_zip_id(self, cursor, uid, ids, zip_id, context=None):
        if not zip_id:
            return {}
        if isinstance(zip_id, list):
            zip_id = zip_id[0]
        bzip = self.pool['res.better.zip'].browse(cursor, uid, zip_id, context=context)
        return {'value': {'zip': bzip.name,
                          'city': bzip.city,
                          'country_id': bzip.country_id.id if bzip.country_id else False,
                          'state_id': bzip.state_id.id if bzip.state_id else False,
                          'zip_id': False 
                          },
                'domain' : {'organization_id' : [('country_id','=', bzip.country_id.id if bzip.country_id else False)]},
                }
dds_staff()
    