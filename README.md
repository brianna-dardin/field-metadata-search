# Salesforce Field Metadata Search

It's a task that can be valuable but utterly tedious and time-consuming for Salesforce admins: analyzing where fields are used within metadata such as validation rules and workflow rules. I was given this task at my current Salesforce job, which gave me the inspiration to try automating it. Of course, better tools already exist, but it seemed like a fun challenge to implement something myself.

The program is currently designed as a command line utility. Download all the files, open the command prompt in that folder and then type "python main.py". This simply prompts you for your login information and the object whose fields you want to analyze. The real meat and potatoes are in the other files. Retrieval.py interacts with the SOAP Metadata API in order to download the relevant metadata files. (Note: only a subset of metadata types are downloaded by default, not everything.) Objectclass.py is home to the... well, Object class. This does the heavy lifting of checking if each field represented in field.py is present in each metadata file. Search.py provides specialized support for metadata files that contain multiple metadata types within it, such as object files, which contain fields, validation rules, etc, or files that can contain multiples of the same type, such as assignment rules. Ultimately, whenever a field is found within a metadata type, it is written to a CSV file for that object. The CSV file can then be used for additional analysis or processing.

### Limitations/Future Enhancements

- This only looks at custom fields. The idea is to focus only on fields that can be deleted, which standard fields cannot.

- This program currently does NOT attempt field disambiguation. That is, it doesn't determine which object the field belongs to. This becomes a major issue if your sObjects share fields with the same API name. To mitigate this somewhat, the filename is also returned in the CSV file. Ultimately, this makes this tool not very useful. In a future update I plan to address this.

- This was designed with smaller orgs in mind that don't have as much metadata to download. This will not be scalable to massive orgs.

- Low priority is to develop a proper UI for this tool, and to also use the website login to obtain the access token.