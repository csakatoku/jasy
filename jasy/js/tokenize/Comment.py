#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Sebastian Werner
#

import logging, re

# Try two alternative implementations
try:
    import misaka

    misakaExt = misaka.EXT_AUTOLINK | misaka.EXT_NO_INTRA_EMPHASIS | misaka.EXT_FENCED_CODE
    misakaRender = misaka.HTML_SKIP_STYLE | misaka.HTML_SMARTYPANTS
    
    def markdown2html(markdownStr):
        return misaka.html(markdownStr, misakaExt, misakaRender)

    logging.debug("Using high performance C-based Markdown implementation")
    
except ImportError as ex:
     
    try:
    
        import markdown
    
        def markdown2html(markdownStr):
            return markdown.markdown(markdownStr)

        logging.debug("Using Python Markdown implementation.")
        
    except:
        
        def markdown2html(markdownStr):
            return markdownStr

        logging.error("Missing Markdown implementation. Please install Misaka (preferred) or Python-Markdown.")




try:
    # http://misaka.61924.nl/#toc_3
    
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name

    codeblock = re.compile(r'<pre(?: lang="([a-z0-9]+)")?><code(?: class="([a-z0-9]+).*?")?>(.*?)</code></pre>', re.IGNORECASE | re.DOTALL)

    def code2highlight(html):
        def _unescape_html(html):
            html = html.replace('&lt;', '<')
            html = html.replace('&gt;', '>')
            html = html.replace('&amp;', '&')
            return html.replace('"', '"')
        
        def _highlight_match(match):
            language, classname, code = match.groups()
            
            # default to Javascript
            if (language or classname) is None:
                language = "javascript"
                
            return highlight(_unescape_html(code), get_lexer_by_name(language or classname or "javascript"), HtmlFormatter(linenos="table"))
            
        return codeblock.sub(_highlight_match, html)
        

except ImportError as ex:
    
    def code2highlight(html):
        return html
    
    logging.error("Syntax highlighting is disabled because Pygments is missing.")
    




# Used to measure the doc indent size (with leading stars in front of content)
docIndentReg = re.compile(r"^(\s*\*\s*)(\S*)")

# Used to split type lists as supported by throw, return and params
listSplit = re.compile("\s*\|\s*")

# Used to remove markup sequences after doc processing of comment text
stripMarkup = re.compile(r"<.*?>")



# Matches return blocks in comments
returnMatcher = re.compile(r"^\s*\{([a-zA-Z0-9_ \.\|\[\]]+)\}")

# Matches type definitions in comments
typeMatcher = re.compile(r"^\s*\{=([a-zA-Z0-9_ \.]+)\}")

# Matches tags
tagMatcher = re.compile(r"#([a-zA-Z][a-zA-Z0-9]+)(\((\S+)\))?(\s|$)")

# Matches param declarations in own dialect
paramMatcher = re.compile(r"@([a-zA-Z0-9]+)(\s*\{([a-zA-Z0-9_ \.\|\[\]]+?)(\s*\.{3}\s*)?((\s*\?\s*(\S+))|(\s*\?\s*))?\})?")

# Matches links in own dialect
linkMatcher = re.compile(r"\{([a-zA-Z0-9_#\.]+)\}")






class CommentException(Exception):
    """
    Thrown when errors during comment processing are detected.
    """

    def __init__(self, message, lineNo=0):
        Exception.__init__(self, "Comment error: %s (line: %s)" % (message, lineNo+1))




class Comment():
    """
    Comment class is attached to parsed nodes and used to store all comment related information.
    
    The class supports a new Markdown and TomDoc inspired dialect to make developers life easier and work less repeative.
    """
    
    # Relation to code
    context = None
    
    # Dictionary of tags
    tags = None
    
    # Dictionary of params
    params = None

    # List of return types
    returns = None
    
    # Static type
    type = None
    
    # Collected text of the comment (without the extracted doc relevant data)
    text = None
    
    # Text of the comment converted to HTML (only for doc comment)
    html = None
    
    
    def __init__(self, text, context=None, lineNo=0, indent="", fileId=None):
        # Store context (relation to code)
        self.context = context
        
        # Store fileId
        self.fileId = fileId
        
        # Convert
        if text.startswith("//"):
            # "// hello" => "   hello"
            text = "  " + text[2:]
            self.variant = "single"
            
        elif text.startswith("/**"):
            # "/** hello */" => "    hello "
            text = "   " + text[3:-2]
            self.variant = "doc"

        elif text.startswith("/*!"):
            # "/*! hello */" => "    hello "
            text = "   " + text[3:-2]
            self.variant = "protected"
            
        elif text.startswith("/*"):
            # "/* hello */" => "   hello "
            text = "  " + text[2:-2]
            self.variant = "multi"
            
        else:
            raise CommentException("Invalid comment text: %s" % text, lineNo)

        if "\n" in text:
            # Outdent indention
            text = self.__outdent(text, indent, lineNo)
            
        else:
            # Strip white space from single line comments
            # " hello " => "hello"
            text = text.strip()

        # Extract docs
        if self.variant == "doc":
            text = self.__processDoc(text, lineNo)
            html = text
            
            # Apply markdown convertion
            if html != "":
                html = markdown2html(html)

                if html == None:
                    html = ""
                else:
                    html = code2highlight(html)
        
            self.html = html
            
            # Post process text to not contain any markup
            if "<" in text:
                text = stripMarkup.sub("", text)
        
        self.text = text
        
    
    
    def getTags(self):
        return self.tags
        


    def __outdent(self, text, indent, startLineNo):
        """
        Outdent multi line comment text and filtering empty lines
        """
        
        lines = []
        for lineNo, line in enumerate((indent+text).split("\n")):
            if line.startswith(indent):
                lines.append(line[len(indent):].rstrip())
            else:
                logging.error("Could not outdent comment at line %s in %s", startLineNo+lineNo, self.fileId)
                return text
                
        # Find first line with real content
        outdentString = ""
        for lineNo, line in enumerate(lines):
            if line != "" and line.strip() != "":
                matchedDocIndent = docIndentReg.match(line)
                
                if not matchedDocIndent:
                    # As soon as we find a non doc indent like line we stop
                    break
                    
                elif matchedDocIndent.group(2) != "":
                    # otherwise we look for content behind the indent to get the 
                    # correct real indent (with spaces)
                    outdentString = matchedDocIndent.group(1)
                    break
                
            lineNo += 1

        # Process outdenting to all lines
        if outdentString != "":
            lineNo = 0
            outdentStringLen = len(outdentString)

            for lineNo, line in enumerate(lines):
                if len(line) <= outdentStringLen:
                    lines[lineNo] = ""
                else:
                    if not line.startswith(outdentString):
                        logging.error("Invalid indention in doc string at line %s in %s", startLineNo+lineNo, self.fileId)
                    else:
                        lines[lineNo] = line[outdentStringLen:]

        # Merge final lines and remove leading and trailing new lines
        return "\n".join(lines).strip("\n")

            
            
    def __processDoc(self, text, startLineNo):

        text = self.__extractStaticType(text)
        text = self.__extractReturns(text)
        text = self.__extractTags(text)
        
        # Collapse new empty lines at start/end
        text = text.strip("\n\t ")

        text = self.__processParams(text)
        text = self.__processLinks(text)
        
        return text            
            
            

    def __splitTypeList(self, decl):
        
        if decl is None:
            return decl
        
        return listSplit.split(decl.strip())



    def __extractReturns(self, text):
        """
        Extracts leading return defintion (when type is function)
        """

        def collectReturn(match):
            self.returns = self.__splitTypeList(match.group(1))
            return ""
            
        return returnMatcher.sub(collectReturn, text)
        
        
        
    def __extractStaticType(self, text):
        """
        Extracts leading type defintion (when value is a static type)
        """

        def collectType(match):
            self.type = match.group(1).strip()
            return ""

        return typeMatcher.sub(collectType, text)
        
        
        
    def __extractTags(self, text):
        """
        Extract all tags inside the give doc comment. These are replaced from 
        the text and collected inside the "tags" key as a dict.
        """
        
        def collectTags(match):
             if not self.tags:
                 self.tags = {}

             name = match.group(1)
             param = match.group(3)

             if name in self.tags:
                 self.tags[name].add(param)
             elif param:
                 self.tags[name] = set([param])
             else:
                 self.tags[name] = True

             return ""

        return tagMatcher.sub(collectTags, text)
        
        
        
    def __processParams(self, text):
        
        def collectParams(match):
            paramName = match.group(1)
            paramTypes = match.group(3)
            paramDynamic = match.group(4) is not None
            paramOptional = match.group(5) is not None
            paramDefault = match.group(7)
            
            if paramTypes:
                paramTypes = self.__splitTypeList(paramTypes)
            
            if self.params is None:
                self.params = {}
            
            # Add new entries and overwrite if a type is defined in this entry
            if not paramName in self.params or paramTypes is not None:
                paramEntry = self.params[paramName] = {}
                
                if paramTypes is not None:
                    paramEntry["type"] = paramTypes
                
                if paramDynamic:
                    paramEntry["dynamic"] = paramDynamic
                    
                if paramOptional:
                    paramEntry["optional"] = paramOptional
                    
                if paramDefault is not None:
                    paramEntry["default"] = paramDefault
            
            return '<code class="param">%s</code>' % paramName
            
        return paramMatcher.sub(collectParams, text)
        
        
        
    def __processLinks(self, text):
        
        def formatTypes(match):
            link = match.group(1).strip()
            return '<a href="#%s"><code>%s</code></a>' % (link.replace("#", ":"), link)
            
        return linkMatcher.sub(formatTypes, text)
        
        
        
        