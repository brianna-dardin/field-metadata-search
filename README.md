# Salesforce Field Metadata Search

It's a task that can be valuable but utterly tedious and time-consuming for Salesforce admins: analyzing where fields are used within metadata such as validation rules and workflow rules. I was given this task at my current Salesforce job, which gave me the inspiration to try automating it. Of course, better tools already exist, but it seemed like a fun challenge to implement something myself.

The program is currently designed as a command line utility. Download all the files, open the command prompt in that folder and then type "python main.py". This simply prompts you for your login information and the object whose fields you want to analyze. The real meat and potatoes are in the other files. Retrieval.py interacts with the SOAP Metadata API in order to download the relevant metadata files. (Note: only a subset of metadata types are downloaded by default, not everything.) Objectclass.py is home to the... well, Object class. This does the heavy lifting of checking if each field represented in field.py is present in each metadata file. Search.py provides specialized support for metadata files that contain multiple metadata types within it, such as object files, which contain fields, validation rules, etc, or files that can contain multiples of the same type, such as assignment rules. Ultimately, whenever a field is found within a metadata type, it is written to a CSV file for that object. The CSV file can then be used for additional analysis or processing.

### Limitations/Future Enhancements

- This only looks at custom fields. The idea is to focus only on fields that can be deleted, which standard fields cannot.

- This program performs field disambiguation (that is, determining whether a mention of a field in a file belongs to the field in the specified object) for everything except code. While it's possible, code is unstructured and unpredictable, which makes disambiguation more challenging. Also, when it comes to relationship fields, the disambiguation only works for fields that are named after the object. For example, Opportunity looks up to CustomObject__c, and the lookup field's API name is also CustomObject__c. This program will find fields prefaced with CustomObject__r and log those, but if the lookup field's API name is SomeOtherName__c, it won't log any fields prefaced with SomeOtherName__r.  

- This was designed with smaller orgs in mind that don't have as much metadata to download. This will not be scalable to massive orgs.

- Low priority is to develop a proper UI for this tool, and to also use the website login to obtain the access token.