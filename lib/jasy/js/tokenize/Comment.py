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

    logging.info("Using high performance C-based Markdown implementation")
    
except ImportError as ex:
    
    try:
    
        import markdown
    
        def markdown2html(markdownStr):
            return markdown.markdown(markdownStr)

        logging.info("Using Python Markdown implementation.")
        
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
                
            return highlight(_unescape_html(code), get_lexer_by_name(language or classname or "javascript"), HtmlFormatter())
            
        return codeblock.sub(_highlight_match, html)
        

except ImportError as ex:
    
    def code2highlight(html):
        return html
    
    logging.info("Syntax highlighting is disabled because Pygments is missing.")
    


# Supports:
# - @param name {Type}
# - @param name {Type?}
# - @param name {Type?defaultValue}
jsdocParamA = re.compile(r"^@(param)\s+([a-zA-Z0-9]+)\s+\{([a-zA-Z0-9_ \.\|\[\]]+)(\s*(\?)\s*([a-zA-Z0-9 \.\"\'_-]+)?)?\}")

# Supports:
# - @param name
# - @param {Type} name 
# - @param {Type} [optionalName=defaultValue]
# - @param {Type} [optionalName]
jsdocParamB = re.compile(r"^@(param)\s+(\{([a-zA-Z0-9_ \.\|\[\]]+)\}\s+)?((\[?)(([a-zA-Z0-9]+)(\s*=\s*([a-zA-Z0-9 \.\"\'_-]+))?)\]?)")

# Supports:
# - @return {Type}
jsdocReturn = re.compile(r"^@(returns?)\s+(\{([a-zA-Z0-9_\.\|\[\]]+)\})?")

# Supports:
# - @throw {Type}
jsdocThrow = re.compile(r"^@(throws?)\s+(\{([a-zA-Z0-9_\.\|\[\]]+)\})?")

# Supports:
# - @deprecated
# - @private
# - @public
# - @static
jsdocFlags = re.compile(r"^@(deprecated|private|public|static)")

# Supports:
# - @name Name
# - @namespace Namespace
# - @requires Name
# - @since Version
# - @version Version
jsdocData = re.compile(r"^@(name|namespace|requires|since|version)\s+(\S+)")

# Supports:
# - @name {Name}
# - @require {Name}
# - @optional {Name}
# - @break {Name}
# - @asset {Path}
jasyMetaData = re.compile(r"^@(name|require|optional|break|asset)\s+(?:\{(\S+)\})")

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
paramMatcher = re.compile(r"@([a-zA-Z0-9]+)(\s*\{([a-zA-Z0-9_ \.\|\[\]]+)((\s*\?\s*(\S+))|(\s*\?\s*))?\})?")

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
    
    The class supports a variety of legacy formats like JSDoc, but comes with a new Markdown and TomDoc
    inspired dialect to make developers life easier and work less repeative.
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
    stype = None
    
    # Collected text of the comment (without the extracted doc relevant data)
    text = None
    
    # Text of the comment converted to HTML (only for doc comment)
    html = None
    
    
    def __init__(self, text, context=None, lineNo=0, indent=""):
        # Store context (relation to code)
        self.context = context
        
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
                logging.error("Could not outdent comment at line %s", startLineNo+lineNo)
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
                        logging.error("Invalid indention in doc string at line %s", startLineNo+lineNo)
                    else:
                        lines[lineNo] = line[outdentStringLen:]

        # Merge final lines and remove leading and trailing new lines
        return "\n".join(lines).strip("\n")

            
            
    def __processDoc(self, text, startLineNo):

        text = self.__extractJsdoc(text)
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
            self.stype = match.group(1).strip()
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
        
        
        
    def __extractJsdoc(self, text):
        """
        Extract classic JSDoc style items with support for both JSDoc like params and qooxdoo like params.
        
        Supports reading of flag and data like JSDoc tags and stores them into new style tags.
        
        See also: http://code.google.com/p/jsdoc-toolkit/wiki/TagReference
        """

        filterLine = False
        remainingText = []

        for line in text.split("\n"):
            
            matched = jsdocParamA.match(line)
            if matched:
                
                paramName = matched.group(2)
                paramTypes = matched.group(3)
                paramOptional = matched.group(5) is not None
                paramDefault = matched.group(6)

                if self.params is None:
                    self.params = {}

                self.params[paramName] = {
                    "optional": paramOptional,
                    "type" : self.__splitTypeList(paramTypes), 
                    "default" : paramDefault
                }

                filterLine = True
                continue


            matched = jsdocParamB.match(line)
            if matched:
                
                paramTypes = matched.group(3)
                paramOptional = matched.group(5) is not ""
                paramName = matched.group(7)
                paramDefault = matched.group(9)
            
                if self.params is None:
                    self.params = {}

                self.params[paramName] = {
                    "optional": paramOptional,
                    "type" : self.__splitTypeList(paramTypes), 
                    "default" : paramDefault
                }
            
                filterLine = True
                continue
                
            
            matched = jsdocReturn.match(line)
            if matched:
                self.returns = self.__splitTypeList(matched.group(3))
                filterLine = True
                continue
            
            matched = jsdocFlags.match(line)
            if matched:
                if self.tags is None:
                    self.tags = {}

                self.tags[matched.group(1)] = True
                continue
            
            matched = jasyMetaData.match(line)
            if matched:
                if self.tags is None:
                    self.tags = {}

                tagName, tagValue = matched.groups()
                if tagName == 'name':
                    self.tags[tagName] = tagValue
                else:
                    self.tags.setdefault(tagName, []).append(tagValue)
                continue

            matched = jsdocData.match(line)
            if matched:
                if self.tags is None:
                    self.tags = {}

                self.tags[matched.group(1)] = matched.group(2)
                continue
            
            # Collect remaining lines
            if filterLine and line.strip() == "":
                filterLine = False
        
            elif not filterLine:
                remainingText.append(line)
                
                
        return "\n".join(remainingText).strip("\n ")
        
        
        
    def __processParams(self, text):
        
        def collectParams(match):
            paramName = match.group(1)
            paramTypes = match.group(3)
            paramOptional = match.group(4) is not None
            paramDefault = match.group(6)
            
            if paramTypes:
                paramTypes = self.__splitTypeList(paramTypes)
            
            if self.params is None:
                self.params = {}
            
            # Add new entries and overwrite if a type is defined in this entry
            if not paramName in self.params or paramTypes is not None:
                self.params[paramName] = {
                    "type" : paramTypes, 
                    "optional": paramOptional,
                    "default" : paramDefault
                }
            
            return '<code class="param">%s</code>' % paramName
            
        return paramMatcher.sub(collectParams, text)
        
        
        
    def __processLinks(self, text):
        
        def formatTypes(match):
            link = match.group(1).strip()
            return '<a href="#%s"><code>%s</code></a>' % (link.replace("#", ":"), link)
            
        return linkMatcher.sub(formatTypes, text)
        
        
        
        
