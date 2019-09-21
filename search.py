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
        for key in self.meta_dict.keys():
            top_level = self.metadata.find_all(key)
            parents = []
            for top in top_level:
                if len(self.meta_dict[key]) > 0:
                    for tag in self.meta_dict[key]:
                        level = top.find_all(tag)
                        if len(level) > 0:
                            for node in level:
                                if self.field.api_name.lower() in node.text.lower():
                                    parents.append(top)
                else: #if len(self.meta_dict[key]) == 0
                    children = top.contents
                    for child in children:
                        if self.field.api_name in child:
                            print(child.name)
                            self._log_match(key,child.name)
            if len(parents) > 0:
                self._log_matches(parents,key)
    
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
            for act in actions:
                if act.find('name'):
                    act_name = act.find('name')
                    for name in names:
                        if name in act_name.text:
                            if 'workflow' in self.meta_type:
                                if act.parent:
                                    parents.append(act.parent)
                            else:
                                parent = self.metadata.findChild(recursive=False)
                                if parent:
                                    parents.append(parent)
            if len(parents) > 0:
                if 'workflow' in self.meta_type:
                    self._log_matches(parents,'rules')
                else:
                    self._log_matches(parents,self.meta_type)
    
    def _log_match(self,key,name):
        print(key,name)
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
                print(key,name)
                
        if len(names) > 0:
            self.field.add_metadata({key : names},self.file_name)
            
    def _get_meta_dict(self):
        for tag in self.metadata.findChildren(recursive=False):
            self.meta_type = tag.name.lower()
            break
        
        if 'object' in self.meta_type:
            self.meta_dict = {'fieldSets' : ['field'],
                'fields' : ['fullName', 'formula', 'controllingField'],
                'listViews' : ['columns','field'],
                'recordTypes' : ['picklist'],
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