from bs4.element import Tag
import re

class Search:
    metadata = None
    field = None
    file_name = ''
    meta_type = ''
    meta_dict = {}
    
    def __init__(self,metadata,field,file_name):
        self.metadata = metadata
        self.field = field
        self.file_name = file_name
        self._get_meta_dict()
        
    def search(self):
        if '.quick' in self.file_name:
            self._search_quick_action()
        elif '.flow' in self.file_name:
            self._search_flow()
        else:
            for key in self.meta_dict.keys():
                top_level = self.metadata.find_all(key)
                parents = []
                for top in top_level:
                    if len(self.meta_dict[key]) > 0:
                        for tag in self.meta_dict[key]:
                            level = top.find_all(tag)
                            if len(level) > 0:
                                for node in level:
                                    if self.field.check_field(node,self.file_name):
                                        parents.append(top)
                    else: #if len(self.meta_dict[key]) == 0
                        children = top.contents
                        for child in children:
                            if isinstance(child, Tag):
                                if self.field.check_field(child,self.file_name):
                                    self._log_match(key,child.name)
                if len(parents) > 0:
                    self._log_matches(parents,key)
    
    def _search_flow(self):
        main_obj = self._find_object('objectType')
        
        fields = []
        pattern = re.compile(r'[^a-zA-Z_.]')
        var_names = ['myVariable_current','myVariable_old']
        meta_text = self.metadata.findChild(recursive=False).text
        for name in var_names:
            indices = re.finditer(name,meta_text)
            for i in indices:
                idx = i.end() + 1
                trun_text = meta_text[idx:]
                pattern_found = pattern.findall(trun_text)
                if len(pattern_found) > 0:
                    char = pattern_found[0]
                    char_idx = trun_text.find(char)
                    fld = trun_text[:char_idx]
                    fields.extend(self._find_relationship(fld, main_obj))
        
        obj_tags = self.metadata.find_all('object')
        for tag in obj_tags:
            if self.field.sobject_name in tag.text:
                field_tags = tag.parent.find_all('field')
                for fld_tag in field_tags:
                    fields.extend(self._find_relationship(fld_tag.text, main_obj))
                  
        tags = self.metadata.find_all('assignToReference')
        for tag in tags:
            if self.field.sobject_name in tag.text:
                fields.extend(self._find_relationship(tag.text, main_obj))
                
        if sum(fields) > 0:
            self._log_match(self.meta_type,self.file_name)
    
    def _search_quick_action(self):
        main_obj = self._find_object('targetObject')
        
        fields = []
        if main_obj:
            tags = self.metadata.find_all('field')
            for tag in tags:
                fields.extend(self._find_relationship(tag.text, main_obj))
        
        if sum(fields) == 0:
            tags = self.metadata.find_all('formula')
            for tag in tags:
                fields.extend(self._find_relationship(tag.text, main_obj))
            
        if sum(fields) > 0:
            self._log_match(self.meta_type,self.file_name)
    
    def _find_object(self, tag):
        main_obj = False
        obj_tags = self.metadata.find_all(tag)
        for obj in obj_tags:
            if self.field.sobject_name in obj.text:
                main_obj = True
                break
        return main_obj
    
    def _find_relationship(self, text, main_obj):
        fields = []
        if self.field.api_name in text:
            relationships = self.field.check_relationship(text)
            if len(relationships) > 0:
                for rel in relationships:
                    if self.field.sobject_name in rel\
                    or self.field.sobject_name.replace('__c','__r') in rel:
                        fields.append(1)
                    else:
                        fields.append(0)
            elif main_obj:
                fields.append(1)
        return fields
        
    def find_templates(self,names):
        temp_tags = ['template','notifyToTemplate']
        templates = []
        for tag in temp_tags:
            templates = self.metadata.find_all(tag)
            if len(templates) > 0:
                break
            
        found_alerts = {}
        if len(templates) > 0:
            for temp in templates:
                for name in names:
                    if name in temp.text:
                        alert = temp.find_parent('alerts')
                        if alert:
                            found_alerts[alert.find('fullName').text] = alert
                        else:
                            tag_name = self.meta_type[:1].lower()\
                                        + self.meta_type[1:-1]
                            self._log_match(tag_name, name)     
                            
        if len(found_alerts) > 0:
            self._log_matches(found_alerts.values(),'alerts')
            self.find_actions(found_alerts.keys())
        
    def find_actions(self,names):
        action_tags = ['action','actions','actionName','escalationAction']
        
        actions = []
        for tag in action_tags:
            actions = self.metadata.find_all(tag)
            if len(actions) > 0:
                break
            
        if len(actions) > 0:
            parents = []
            parent = self.metadata.findChild(recursive=False)
            for act in actions:
                if act.find('name'):
                    act_name = act.find('name')
                    for name in names:
                        if name in act_name.text:
                            if self.field.sobject_name in self.file_name:
                                if 'workflow' in self.meta_type\
                                and act.parent:
                                    parents.append(act.parent)
                                elif parent:
                                    parents.append(parent)
                            elif 'flow' in self.meta_type and parent:
                                parents.append(parent)
                                
            if len(parents) > 0:
                if 'workflow' in self.meta_type:
                    self._log_matches(parents,'rules')
                else:
                    self._log_matches(parents,self.meta_type)
    
    def _log_match(self,key,name):
        self.field.add_metadata({key : [name]},self.file_name)
            
    def _log_matches(self,parents,key):
        names = []
        for parent in parents:
            name = None
            if parent.find('fullName',recursive=False):
                name = parent.find('fullName',recursive=False).text
            elif parent.find('label',recursive=False):
                name = parent.find('label',recursive=False).text
            elif parent.find('masterLabel',recursive=False):
                name = parent.find('masterLabel',recursive=False).text
            if name:
                names.append(name)
                
        if len(names) > 0:
            self.field.add_metadata({key : names},self.file_name)
            
    def _get_meta_dict(self):
        tag = self.metadata.findChild(recursive=False)
        self.meta_type = tag.name.lower()
        
        if 'object' in self.meta_type:
            self.meta_dict = {'fieldSets' : ['field'],
                'fields' : ['formula', 'controllingField'],
                'listViews' : ['columns','field'],
                'searchLayouts' : [],
                'validationRules' : ['errorConditionFormula', 'errorDisplayField'],
                'webLinks' : ['url']}
        elif 'workflow' in self.meta_type:
            self.meta_dict = {'alerts' : ['field'],
                 'fieldUpdates' : ['field', 'formula'],
                 'rules' : ['field', 'formula', 'offsetFromField']}
        elif 'assignment' in self.meta_type:
            self.meta_dict = {'assignmentRule' : ['field', 'formula']}
        elif 'autoresponse' in self.meta_type:
            self.meta_dict = {'autoResponseRule' : ['field']}
        elif 'escalation' in self.meta_type:
            self.meta_dict = {'escalationRule' : ['field']}
        elif 'matching' in self.meta_type:
            self.meta_dict = {'matchingRules' : ['fieldName']}
        elif 'sharing' in self.meta_type:
            self.meta_dict = {'sharingCriteriaRules' : ['field']}