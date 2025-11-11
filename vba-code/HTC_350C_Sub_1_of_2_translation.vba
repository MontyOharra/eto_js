'From HTC350C_1of2_Translation of 1/28/2023
' Copyright © 2022-2023 Thomas F. Crabtree, Jr. All rights reserved

Option Compare Database
Option Explicit
Option Base 1

Dim VersionID As String
Dim VersionChange As String

Dim Msg As String, MsgTitle As String, Ans As Integer

Dim F_FNs(1000)
Dim F_DTRNs(1000)
Dim MaxF As Integer, f As Integer, EndF As Integer

'    The "This..." variables are filled out as the process continues for each PDF/txt set
'       of records for the email is processed and written to the ETOLog table at the end
'       of the process for the email in question

Dim ELThisRun As Date                 'assigned to all records of this execution
Dim ELThiseMail As String             'assigned to all PDfs associated with the email being processed (Date & Subject)
Dim ELThisLineNo As Integer           'provide for multiple lines per email
Dim ELThisFilePath As String          'Full path of .txt being processed
Dim ELThisSender As String            'ditto
Dim ELThisCustomerID As Integer       'ditto
Dim ELThisHAWB As String              'ditto
Dim ELThisOrderCreated As Boolean     'indicates if an order was created using the info in the email
Dim ELThisOrderNbr As Double          'order number matching the customer/hawb already in the system or
                                      '  the order number assigned by the ETO process
Dim ELThisProcessedOK As Boolean      'true => no errors were encounter processing this pdf/txt
Dim ELThisComment As String           'if process errors were encountered in the email, this
                                      '  is where the error condition(s) are documented


Sub HTC350C_1of2_Translation()
' ----------------------------------------------------------------
' Copyright © 2022-2023 Thomas F. Crabtree, Jr. All rights reserved
' Procedure Name: HTC200C_1of2_Translation
' Purpose: Interpret SOS forms attached to emails to create new orders or
'           add to or alter info on existing orders
' Procedure Kind: Sub
' Procedure Access: Public
' Parameter wELThisRun (Date): Identifies this run of the parsing process
' Parameter wELThisEmail (String): Identfies the email to which this form was attached
' Parameter wELThisLineNo (Integer): Sequences the log file entry in relation to the email
' Parameter wThisFileWithPath (String):Full path and filename of the txt file
' Parameter wThisSender (String):contains the email address of the sender
' Author: Tom Crabtree
'
' Date: 2022-12-13 Bulletproofed
' Date: 2022-12-27 Added code to redesign how the delivery date and time span is derived.
'            VersionID = "Version 2.06, 12-19-202211:09 PM"
'             VersionChange = "1. Changed BOL and Routing modules to deal with a pickup date/time " & _
'                              "   ending with a '-'" & _
'                              "2. Added code to delete logfile records and their associated files when " & _
'                              "   older than the specified retention (14 days as of this change)." & _
'                              "3. Corrected the filename used with ModuleFailed to id the offending record."'
'            VersionID = "2.0, 2002-11-25 11:12 AM"
'            VersionChange = "Fixed to handle txt files with no info correctly;" & vbCrLf & _
'                            " Fixed to delete ONLY the matching WLI record;" & vbCrLf & _
'                            " Show versionid on all displays;" & _
'                            " Show Email Subject in associated HTC Order History."
'
'            VersionID = "02.01,2022-11-28 09:29 AM"
'            VersionChange = "Complete repair that deleted ONLY the WLI record " & _
'                            "created to accomplish the ETO process when process completes."
'            VersionID = "2.02, 22-12-04 05:52 AM"
'            VersionChange = "Change SOS Alert to add any available pickup or delivery info" & _
'                              "when the address isn't found."
'            VersionID = "2.03, 22-12-06 7:51 AM"
'            VersionChange = "Repaired 'HTC200F_FA_Fastbook' to look for HTC350 Air Freight codes" & _
'                            "instead of HTC210..."
'            VersionID = "2.04, 22-12-14 1:27 PM"
'            VersionChange = "1. changed action to remove ETO's login instance from removing the 1st it " & _
'                                 "finds to All it finds (i.e. ready for more than one instance)." & _
'                            "2. If an order has already been created for this customer / HAWB then the " & _
'                            "   order information is classified as 'Regarding existing order' even if the " & _
'                            "   customer, or pickup locn or delivery location is not known." & _
'                            "3. func_NameSubs-01-00 changed to limit substitions to active NameSwap entries" & _
'                            "4. Worked over ETO translation routines adding error traps and bullet-proofing " & _
'                            "   the modules. "
'            VersionID = "2.05, 22-15-15 9:50"
'            VersionChange = "Added 'Resume Next' to error routine in HTC350C_1of2_Translation"
'            VersionID = "2.10, 23-02-03 12:02"
'            VersionChange = (1) Beefed up the log entry process here and in 2of2_CreateOrders and
'                                the error trapping processes.
'                            (2) Added process to order number and HAWB from Battery Advisory 2
'                                Since the 1st line of the txt file is the same as a previous
'                                pattern, I had to deal with the fact some, but not all, the lines
'                                in the pattern may not match.
'                            (3) Repaired the log maintenance process to keep only defined period's
'                                worth of log entries and related txt and pdf files.
'
'            VersionID = 2.11, 2023-03-27 08:00 AM
'            VersionChange = (1) Work over the on error procedures in Alert and Dlvry Receipt
'                            (2) Deal with Alerts with multiple HAWB's defined copying One
'                                (and only one) PDF per HAWB listed.
'
'            VersionID = 2.12, 2023-04-03 12:08 PM
'            VersionChange = (1) Found error in Processing a SOS Routing form that caused the CARRIER:
'                                field to be overlooked.  This change repaired that problem.
'            Version ID = 2.13, 2023-04-06 5:35 PM
'            VersionChange = (1) Found a circumstance where the BOL module read past the last record
'                                of the form and posted the FileEnd in line as part of the form.
'                                Error caused the 'Bld-eMail routine to fail by allowing email line
'                                count to exceed max value an integer can represent.
'                            (2) added extra lines to the Bld_eMail routine to insure I don't get into a loop
'                                creating blank lines on the email to dispatch.  (Not sure why this happens,
'                                but it has twice in the recent past).
'             Version ID = 2.20  2024-05-28
'             VersionChange =(1) SOS changed practices with creating MAWB, think change was not uniform, so
'                                I added pattern 14 to accommodate the new MAWB format.  Note the changes did
'                                NOT affect the the MAWB process module itself, only the process to identify the
'                                entry as a MAWB submission.
'                            (2) I updated the HTC350C_PurgePDFFiles to examine the folder containing PDFs/Txts
'                                saved processed records to remove any files more than 30 days old.  Thought I'd
'                                done this, but apparently not, so I added it in here.
'             Version ID = 2.21  2024-06-01
'                            (1) For reasons unknown, Access is sometimes corrupting 'AllParsedPDFs.txt' into
'                                'AllParsedPDFs#txt'.  I created a new txt name (AllParsedPDFsName), set it to
'                                the linked filename, and use the new txtname in the set statemen
'                                the set statement, then used that new txtname in the set statement.  We'll see.
'             Version ID = 2.22  2024-12-03
'                            (2) Added customer to pattern array in preparation for expanding ETO to customers
'                                other than SOS Global
'             Version ID = 2.23 2025-06-25
'                             (1) The routing form header changed from "SOSGLOBAL Routing Instructions" changed to
'                                 "SOS GLOBAL INC Routing Instructions".  Prior to the change, the pdf's were begin
'                                 rejected as an undefined form.  Change was made this date approx 4:40 pm.
'             Version ID = 2.24 2025-07-01
'                             (1) Format 9, SOS Battery Advisory changed in the the SOS pickup number changed from
'                                 6 digits to 7 digits.  I adjusted the format accordingly.
'
' ----------------------------------------------------------------

'Stop

     VersionID = "Version ID = 2.24, 2025-07-01 10:59 AM"

     Dim ModuleName As String             'Identifies module to the error handler
     Dim ModLocnMark As String            'Marks beginning of each major process

     ModuleName = "HTC350C_1of2_Translation"
     ModLocnMark = "MLC 01"
'==========================================================================================
On Error GoTo ModuleFailed

        Dim Msg As String: Msg = ""
        Dim HAWBProcessed As Boolean

        ELThisRun = Now()  'set this once per execution of the ETO process
        ELThisLineNo = 0

        MsgTitle = "HTC350C_1of2_Translation"
       
        MaxF = 1000
'Stop
        Dim db As Database: Set db = CurrentDb
          
        Dim xServerName As String: xServerName = "HarrahServer"
        Dim xPCName As String: xPCName = "HarrahServer"
        Dim xPCLID As String: xPCLID = "ETOProcess"
        Dim xWhosLoggedIn As String: xWhosLoggedIn = "HarrahServer"
        
        Dim WLI As Recordset
        Set WLI = db.OpenRecordset("HTC000 WhosLoggedIn", dbOpenDynaset)
         
        With WLI
            .AddNew
                !wli_company = 1
                !wli_branch = 1
                !wli_homeserver = xServerName
                !wli_servertype = "network"
                !wli_staffid = 0
                !pcname = xPCName
                !pclid = xPCLID
                !WhosLoggedIn = xWhosLoggedIn
                !securitylevel = 10
                !logintime = Now()
            .Update
            .MoveFirst
            Do Until !wli_company = 1 And !wli_branch = 1 And _
                     !pcname = Environ("computername") And _
                     !pclid = Environ("username") And _
                     !wli_staffid = 0
                     Exit Do
                .MoveNext
            Loop
            If .EOF Then
                Msg = "Can't find WhosLoggedIn Just created"
                Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
            End If
        End With
        
        
        Dim wCoID As String: wCoID = WLI!wli_company
        Dim wBrID As String: wBrID = WLI!wli_branch
        Dim wHomeServer As String: wHomeServer = WLI!wli_homeserver
        Dim wServerType As String: wServerType = WLI!wli_servertype
        Dim wStaffID As Integer: wStaffID = WLI!wli_staffid
        Dim wPCName As String: wPCName = WLI!pcname
        Dim wPCLid As String: wPCLid = WLI!pclid

'Stop
        Dim wWhosLoggedIn As String: wWhosLoggedIn = WLI!WhosLoggedIn
        Dim wSecLvl As Integer: wSecLvl = WLI!securitylevel
        Dim DaysLogFileRecordLives As Integer   '<== 2023-01-17 changed from string to integer
        
        DaysLogFileRecordLives = 31
        
        Dim X As Integer, MaxX As Integer, EndX As Integer 'defines a pattern
        Dim Y As Integer, EndY As Integer                  'defines a line in the pattern
        Dim Z As Integer, MaxZ As Integer, EndZ As Integer 'defines charachter in the line of a pattern
        
        'Logfile contains at least one record per email attachment used for short term history
        'and error reporting and any diagnostic messages that indicate notable conditions '
        'encountered in the process.
        '
        'Note Logfile records live on the log file for nbr of days defined in
        '"DaysLogFileRecordLives" after which they are deleted.
        
        Dim Logfile As Recordset
        Set Logfile = db.OpenRecordset("HTC350_G800_T010 ETOLog", dbOpenDynaset)

        Dim MisplacedRecCount As Integer
        
        Dim ThisFormatName As String
        Dim ThisFileName As String
        Dim ThisSender As String
        Dim ThisPDFName As String
        Dim ThisTxtFileName As String
        
        Dim wrkArea As String
        Dim wrkArea2 As String
        Dim wrkSigLine As String
        Dim wrkSigPortion As String
        Dim LineSkipped As Boolean: LineSkipped = False
        Dim RowMatches As Boolean: RowMatches = False
        Dim PatternMatches As Boolean: PatternMatches = False
        Dim AlphaStuff As String: AlphaStuff = " abcdefghijklmnopqrstuvwxyz/0123456789"
        
        Dim TxtFormatSig(100) As String
        Dim TxtFormatName(100) As String
        Dim TxtFormatLength(100) As Integer
        Dim TxtFormatHasInfo(100) As Boolean
        Dim TxtFormatCustomer(100) As String
        
        Dim wrk_txtdoctype As String, wtxtProcessYN As Boolean
        Dim wrk_TxtCustomerID As Integer, wrk_TxtCustomer As String
        Dim wrk_txtHAWB As String, wrk_txtMAWB As String
        Dim wrk_TxtPkupFromID As Double, wrk_TxtPkupFromName As String, wrk_TxtPkupFromAddress As String
        Dim wrk_TxtPkupFromNotes As String
        Dim wrk_TxtPkupDate As String, wrk_TxtPkuptime As String
        Dim wrk_TxtDelToID As Double, wrk_TxtDelToName As String, wrk_TxtDelToAddress As String
        Dim wrk_TxtDelToNotes As String
        Dim wrk_TxtDelDate As String, wrk_TxtDelTime As String
        Dim wrk_TxtQty As Integer, wrk_TxtWeight As Integer
        Dim wrk_TxtComments As String
        Dim wrk_TxtProcessYN As Boolean
        Dim wrk_TxtHasInfo As Boolean
        Dim wrkFilePath As String
        Dim InitialPath As String
        Dim Processpath As String
        Dim UnrecognizedPath As String
        Dim ETO_Date As Date
        Dim NormalEnd As Boolean
        
        InitialPath = "C:\HTC_Parsed"
        Processpath = "C:\HTC_Processed Attachments"
        UnrecognizedPath = "C:\HTC_Unrecognized Attachment"
        
        'Remove Log file rows and associated .PDF and .TXT files
        'older than the proscribed time (DaysLogFileRecordLives)

        Dim fso As FileSystemObject
        With Logfile
            If Not .EOF Then
                .MoveFirst

                On Error Resume Next
                Do Until .EOF
                    For X = 1 To Len(Trim(!etolog_thisrun))
                        If Mid(!etolog_thisrun, X, 1) = " " Then Exit For
                    Next X
                    wrkArea = Left(!etolog_thisrun, X - 1)
                    If IsDate(wrkArea) Then
                        ETO_Date = CDate(wrkArea)
                        If DateDiff("d", ETO_Date, Date) > DaysLogFileRecordLives Then
                        'if the associated txt and pdf files live in the Processed folder, remove them
                            wrkFilePath = Replace(!etolog_filepath, InitialPath, Processpath)
                            If fso.FileExists(wrkFilePath) Then Kill wrkFilePath
                            wrkFilePath = Replace(wrkFilePath, ".txt", ".pdf")
                            If fso.FileExists(wrkFilePath) Then Kill wrkFilePath
                                
                            'if the associated txt and pdf files live in the Unrecognized folder, remove them
                            wrkFilePath = Replace(!etolog_filepath, InitialPath, UnrecognizedPath)
                            If fso.FileExists(wrkFilePath) Then Kill wrkFilePath
                            wrkFilePath = Replace(wrkFilePath, ".txt", ".pdf")
                            If fso.FileExists(wrkFilePath) Then Kill wrkFilePath
                                
                            'without regard to presence/absence of the files retained for potential
                                'use in diagnostics, remove the Log file entry
                            .Delete
                        End If
                    End If
                    .MoveNext
                Loop
            End If
        End With

On Error GoTo ModuleFailed
        
        ' The WLI Info is provided behind the dim statements above
        'Call HTC200B_GetWLIInfo(wCoID, WBrID, wServer, wPCName, wPCLid, wWhosLoggedIn, wSecLvl)
        
        'EachPDF is a table with each row containing information extracted from
        'each pdf-to-txt file

            Dim EachPDF As Recordset
            Set EachPDF = db.OpenRecordset("HTC200F_TxtFileNames", dbOpenTable)

        'Run a Query to create a table of all parsed txts in File number,
        '    Del Rcpt number, and Line Sequence in that order.

            DoCmd.SetWarnings False
   'Stop
                DoCmd.OpenQuery "HTC200F_G030_Q000A AllParsedPDFs Tbl Created"
            DoCmd.SetWarnings True
        '==================================================================================
        
        'Dim WrkTxtFile As Recordset
        'Set WrkTxtFile = db.OpenRecordset("HTC200F_G030_Q030 WrkTxtFile", dbOpenDynaset)
        
        MaxX = 100 'maximum number of patterns

        TxtFormatSig(1) = "SOS GLOBAL EXPRESS INC ROUTING INSTRUCTIONS"
        TxtFormatName(1) = "SOS Routing"
        TxtFormatHasInfo(1) = True
        TxtFormatCustomer(1) = "SOSGlobal"
        
        TxtFormatSig(2) = "##|########"
        TxtFormatName(2) = "SOS BOL"
        TxtFormatHasInfo(2) = True
        TxtFormatCustomer(2) = "SOSGlobal"
        
        TxtFormatSig(6) = "###########|##|########"
        TxtFormatName(6) = "SOS BOL2"
        TxtFormatHasInfo(6) = True
        TxtFormatCustomer(6) = "SOSGlobal"
        
        TxtFormatSig(7) = "###|########"
        TxtFormatName(7) = "SOS BOL3"
        TxtFormatHasInfo(7) = True
        TxtFormatCustomer(7) = "SOSGlobal"
        
        TxtFormatSig(3) = "D E L I V E R Y   R E C E I P T                 ###############"
        TxtFormatName(3) = "SOS Dlvry Rcpt"
        TxtFormatHasInfo(3) = True
        TxtFormatCustomer(3) = "SOS Global"

        TxtFormatSig(4) = "AAA       LL           EEEEEEEEE    RRRRRRRR     TTTTTTTTTT"
        TxtFormatName(4) = "SOS Alert"
        TxtFormatHasInfo(4) = True
        TxtFormatCustomer(4) = "SOSGlobal"
        
        TxtFormatSig(5) = "###   ###   ########                                        ###########"
        TxtFormatName(5) = "SOS MAWB1"
        TxtFormatHasInfo(5) = True
        TxtFormatCustomer(5) = "SOSGlobal"
         
        TxtFormatSig(8) = "SOS GLOBAL EXPRESS, INC." & "|" & "Date:" & "|" & "Hawb Number:" & "|" & "Type of first ID reviewed:"
        TxtFormatName(8) = "SOS Cargo Acceptance"
        TxtFormatHasInfo(8) = False
        TxtFormatCustomer(8) = "SOSGlobal"
        
        TxtFormatSig(9) = "For SOS Global Internal / SOS Global Agent use only" & "|" & "*** THIS FORM MUST BE PROVIDED TO THE AIRLINE AT TIME OF TENDER ***" & "|" & "SOS Pickup #######  / SOS HAWB ########"
        TxtFormatName(9) = "SOS Battery Advisory"
        TxtFormatHasInfo(9) = False
        TxtFormatCustomer(9) = "SOSGlobal"
        
        TxtFormatSig(10) = "SOS GLOBAL EXPRESS, INC." & "|" & "Date:" & "|" & "Hawb Number:" & "|" & "Type of first ID reviewed:"
        TxtFormatName(10) = "SOS SOS IACQ Form"
        TxtFormatHasInfo(10) = False
        TxtFormatCustomer(10) = "SOSGlobal"
        
        TxtFormatSig(11) = "WAYBILLNUMBER:###-########NAMESTREET ADDRESSCITYCONTACTSTATE/" & "ZIPNAMESTREET ADDRESSCITYCONTACTSTATE/ZIPTELEPHONE NO."
        TxtFormatName(11) = "SOS Forward Air Fast Book"
        TxtFormatHasInfo(11) = True
        TxtFormatCustomer(11) = "SOSGlobal"
        
        TxtFormatSig(12) = "Rev: ####-##-## THIS PICKUP IS SUBJECT TO TSA INSPECTION REQUIREMEN TS."
        TxtFormatName(12) = "SOS Inspection Notification"
        TxtFormatHasInfo(12) = False
        TxtFormatCustomer(12) = "SOSGlobal"
        
        TxtFormatSig(13) = "For SOS Global Internal / SOS Global Agent use only" & "|" & "SOS Pickup ######   / SOS HAWB ########"
        TxtFormatName(13) = "SOS Battery Advisory 2"
        TxtFormatHasInfo(13) = True
        TxtFormatCustomer(13) = "SOSGlobal"
        
        '2024-05-24: Alternate format of MAWB Established
        TxtFormatSig(14) = "###   ###   #### ####                                       ### #### ####"
        TxtFormatName(14) = "SOS MAWB2"
        TxtFormatHasInfo(14) = True
        TxtFormatCustomer(14) = "SOSGlobal"

        EndX = 14 'Number of signature lines (TxtFormatNames,Signatures)
            
        'Check to insure the AllParsedPDF's table is not empty
        Dim AllParsedPDFsName As String: AllParsedPDFsName = "AllParsedPDFs"
        
        Dim allparsedpdfs As Recordset
        Set allparsedpdfs = db.OpenRecordset(AllParsedPDFsName, dbOpenDynaset)
        
        allparsedpdfs.MoveFirst
        allparsedpdfs.MoveLast
        If allparsedpdfs.RecordCount = 0 Then
            With Logfile
                .AddNew
                    !etolog_thisrun = ELThisRun
                    !etolog_lineno = ELThisLineNo
                    !etolog_emailid = "PDF Folder is empty"
                    !etolog_processedok = True
                    !etolog_comment = "There are no PDF's to process. This run is closed."
                .Update
            End With
            Application.Quit
        End If
   'Stop
        Call HTC200F_RemoveEmptyTxtFiles 'removes null lines from input AND any files that
                                         ' have nothing but null or empty lines between the
                                         ' file start and file end markers.
        
        'Check for an empty file (nothing between filestart and fileend)
    
    ModLocnMark = "MLC 02"
   
        Dim AllParsedPDF_Sorted As Recordset
        Set AllParsedPDF_Sorted = db.OpenRecordset("HTC200F_G030_Q000B All ParsedPDFs Sorted", dbOpenDynaset)

        'If I find an instance in the txt files where there's nothing between the file header and file trailer
        ' then make note in the log file and delete the file header and trailer from the input file
        
        With AllParsedPDF_Sorted
            .MoveFirst
            Do Until .EOF
                If Left(!txtline, 13) = "**Filestart**" Then
                    .MoveNext
                    wrkArea = !txtline
                    If Left(wrkArea, 11) = "**FileEnd**" Then
                        Logfile.AddNew
                            ELThisLineNo = ELThisLineNo + 1
                            Logfile!etolog_thisrun = ELThisRun
                            Logfile!etolog_emailid = Mid(wrkArea, InStr(wrkArea, "DTR_"), InStr(wrkArea, "_xxx_") - 1)
                            Logfile!etolog_lineno = ELThisLineNo
                            
                            wrkArea = !txtline
                            Logfile!etolog_filepath = Replace(wrkArea, "**FileEnd**", "")
                            
                            wrkArea2 = Left(wrkArea, InStr(wrkArea, "_xxx_") + 4)
                            wrkArea = Replace(wrkArea, wrkArea2, "")
                            Logfile!etolog_sender = Left(wrkArea, InStr(wrkArea, "_xxx_") - 5)
                            
                            Logfile!etolog_customerid = 0
                            Logfile!etolog_hawb = "None"
                            Logfile!etolog_ordercreated = False
                            Logfile!etolog_orderno = 0
                            Logfile!etolog_processedok = False
                            Logfile!etolog_comment = "No Parsed Records between the file markers"
                        Logfile.Update
                        .MovePrevious
                        .Delete
                        .MoveNext
                        .Delete
                    Else
                        .MoveNext
                    End If
                End If
                .MoveNext
            Loop
        End With
        
        'Following procedure restructures the parsed pdf data so that an SOS
        'having more than one Delivery Receipt is broken out into one SOS Alert
        'for each delivery receipt, then assigns file number, Delivery Receipt
        'number and line number to each record creating a table of parsed text
        'data in that sequence.

'Stop

         Call prep_AllParsedPDFs(TxtFormatSig(4), wCoID, wBrID, ELThisLineNo, NormalEnd)
        If Not NormalEnd Then
            DoCmd.OpenForm "HTC200F_G010_F010A Position"
            With Forms![HTC200F_G010_F010A Position]
                !lbl_FilePosition.Caption = vbCrLf & "Process Terminated" & vbCrLf & _
                                            "Empty input or Code Error, See ETO Log"
                !lbl_Version.Caption = VersionID
                .Refresh
                .Repaint
            End With
            
            Call HTC200F_Wait(5)
            
            Application.Quit
        End If
        
            
        '=======================================================================
  'Stop
        Dim AllTXTs As Recordset
        Set AllTXTs = db.OpenRecordset("HTC200F_G030_Q000B All ParsedPDFs Sorted", dbOpenDynaset)
        
        'Scan the TXTs table to create and array with all unique values of
        'File number and Dtrn number.
    'Stop
    
    ModLocnMark = "MLC 03"
    
            With AllTXTs
                f = 0
                .MoveFirst
                Do Until .EOF
                    If f > MaxF Then
                        Msg = ELThisRun & "; 1 of 2 Translation: The number of parsed PDFs exceed maximum of " & MaxF
                        
                        'if too many pdfs are to be processed, back up to the last "**FileEnd**"
                        'and remove all pdfs after the last complete set was created.
                        
                        Do Until Left(!txtline, 11) = "**FileEnd**"
                            .MovePrevious
                        Loop
                        
                        ELThisFilePath = Replace(!txtline, "**FileEnd**", "")
                        
                        Msg = Msg & " PDF's. The last email processed was stamped " & Mid(!txtline, InStr(!txtline, "DTR_" + 4, InStr(!txline, "_xxx_") - 1))
                                        
                        .MoveNext '<== move to the Filestart that can't be completed.
                        
                        Do Until .EOF
                            .Delete
                            .MoveNext
                        Loop
                        
                        ELThisLineNo = ELThisLineNo + 1
                         Logfile.AddNew
                            Logfile!etolog_thisrun = ELThisRun
                            Logfile!etolog_emailid = ThisTxtFileName
                            Logfile!etolog_lineno = ELThisLineNo
                            Logfile!etolog_filepath = ELThisFilePath
                            Logfile!etolog_sender = ""
                            Logfile!etolog_customerid = 0
                            Logfile!etolog_hawb = wrk_txtHAWB
                            Logfile!etolog_ordercreated = False
                            Logfile!etolog_orderno = 0
                            Logfile!etolog_processedok = True
                            Logfile!etolog_comment = Msg
                        Logfile.Update
                        Exit Do
                    Else
                        If Left(!txtline, 13) = "**FileStart**" Then
                            f = f + 1: F_FNs(f) = !FN: F_DTRNs(f) = !DTRN
                        End If
                        .MoveNext
                    End If
                Loop
                EndF = f
            End With

        'Empty EachPDF (HTC200F_TxtFileNames) content loaded by the last run of this process
        
    ModLocnMark = "MLC 04"
        
        With EachPDF
            If Not .EOF Then
                .MoveFirst
                Do Until .EOF
                    .Delete
                    .MoveNext
                Loop
            End If
        End With
        
        'Empty the Pattern(x,y) array

        Dim PatternLn(25, 25) As String
        Dim LineMatches(25, 25) As Boolean
        
        For X = 1 To EndX
            For Y = 1 To 25
                PatternLn(X, Y) = ""
                LineMatches(X, Y) = False
            Next Y
        Next X

       '************ Use the TxtFormatSig item to build a corresponding set of pattern lines
        '************ Hereafter, X relates to a TxtFormatSig item (1st dim of PatternLn)
        '*********************** Y relates to a PatternLN (2nd dim of PatternLn)
        '*********************** Z relates to a character position in both wrkTxtLine and PatternLn(X,Y)

        'for each pattern, build a pattern table and compare it to the txt file

        For X = 1 To EndX                                   ' for each pattern; Note changed from MaxX to EndX on 7/2/2025 Tom C
            wrkSigLine = TxtFormatSig(X)
            Y = 1
            
            For Z = 1 To Len(Trim(wrkSigLine))
                If Mid(wrkSigLine, Z, 1) = "|" Then     'go to the next line in the pattern
                    Y = Y + 1
                Else
                    PatternLn(X, Y) = PatternLn(X, Y) & Mid(wrkSigLine, Z, 1)
                End If
            Next Z
            Y = Y + 1
            PatternLn(X, Y) = "End of Pattern"
        Next X

    '************************************************************************
    '***** All patterns are loaded into the patternln(x,y) table       ******
    '************************************************************************
 'Stop
    ModLocnMark = "MLC 05"
    
    '************************************************************************
        'For each file loaded into all parsed pdf's
        '   load TxtFile table with all rows of the file to be processed
        '   examine input against patternln for match
        '   make entry into HTC200F_txtFileNames
    '************************************************************************
         
        Dim FileToProcess As Recordset
        Set FileToProcess = db.OpenRecordset("HTC200F_G030_T030 File To Process", dbOpenTable)
        
        'Forms![HTC200F_G010_F010A Position]!lbl_Version.Caption = VersionID
        
        Dim Txts As Recordset
        Set Txts = db.OpenRecordset("HTC200F_G030_Q030 WrkTxtFile", dbOpenDynaset)
'Stop
        DoCmd.OpenForm "HTC200F_G010_F010A Position"
        Forms![HTC200F_G010_F010A Position]!Label3.Caption = "HTC Email to Order, Step 1 of 2"
        Forms![HTC200F_G010_F010A Position]!lbl_Version.Caption = VersionID
        Forms![HTC200F_G010_F010A Position].Repaint
        
        'Identify by File Nbr and DTRN number the pdf parsed txt file records to process
        ' and process all the records so identified
            For f = 1 To EndF
                Forms![HTC200F_G010_F010A Position]!lbl_FilePosition.Caption = F_FNs(f) & " - " & F_DTRNs(f)
                Forms![HTC200F_G010_F010A Position]!lbl_Version.Caption = VersionID
                Forms![HTC200F_G010_F010A Position].Repaint
    'Stop
                ' Clear wrk fields
                
                wrk_txtdoctype = "": wrk_TxtCustomerID = 0: wrk_TxtCustomer = ""
                wrk_txtHAWB = "": wrk_txtMAWB = ""
                wrk_TxtPkupFromID = 0: wrk_TxtPkupFromName = "": wrk_TxtPkupFromAddress = ""
                wrk_TxtPkupFromNotes = ""
                wrk_TxtPkupDate = "": wrk_TxtPkuptime = ""
                wrk_TxtDelToID = 0: wrk_TxtDelToName = "": wrk_TxtDelToAddress = ""
                wrk_TxtDelToNotes = ""
                wrk_TxtDelDate = "": wrk_TxtDelTime = ""
                wrk_TxtQty = 0: wrk_TxtWeight = 0
                wrk_TxtComments = ""
                wrk_TxtProcessYN = False

                'Load this 'File To Process' with the current value of FN and DTRN
                    
                If FileToProcess.RecordCount > 0 Then
                    FileToProcess.MoveFirst
                    Do Until FileToProcess.EOF
                        FileToProcess.Delete
                        FileToProcess.MoveNext
                    Loop
                End If
                FileToProcess.AddNew
                    FileToProcess!currFN = F_FNs(f)
                    FileToProcess!currdrtn = F_DTRNs(f)
                FileToProcess.Update
                'Process the subset of parsed pdf records (i.e. from a single pdf document)
                
                Txts.Requery
    'Stop
                With Txts

    ModLocnMark = "MLC 06"
                    
                    'Step 1, identify the format of pdf translated

                    .MoveFirst
                    If Left(!wrktxtline, 13) <> "**FileStart**" Then
                        Msg = "A. The first line of the work file is NOT a file header"
                        Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
                        If Not .EOF Then
                            .MoveFirst
                            Do Until Left(!wrktxtline, 13) = "**FileStart**"
                              .MoveNext
                            Loop
                        End If
                        GoTo ModuleFailed
                    End If
        
                    ThisFileName = Trim(Right(!wrktxtline, Len(!wrktxtline) - 13))
                    ELThisFilePath = ThisFileName
  'Stop
                    ELThisFilePath = Replace(!wrktxtline, "**FileStart**", "")
                    ELThiseMail = HTC200F_EM_DtTm(ThisFileName) & " " & HTC200F_EM_Subject(ThisFileName, ThisSender)
                    ThisFileName = Replace(ThisFileName, "C:\HTC_Parsed_PDF\", "")
                    ThisTxtFileName = Left(ThisFileName, InStr(ThisFileName, "_xxx_") - 1)
'Stop
                    'ID the sender
                    X = InStr(ThisFileName, "_xxx_") + 5
                    wrkArea = Right(ThisFileName, Len(ThisFileName) - X + 1)
                    ThisSender = Left(wrkArea, InStr(wrkArea, "_xxx_") - 1)

                    Forms![HTC200F_G010_F010A Position]!lbl_FilePosition.Caption = !wrktxtfn & " - " & !wrktxtdtrn & " ==> " & ThisFileName
                    Forms![HTC200F_G010_F010A Position]!lbl_Version.Caption = VersionID
                    Forms![HTC200F_G010_F010A Position].Repaint
                    
                    X = 1: Y = 1

                    ThisPDFName = ThisFileName
                    .MoveNext   '<= Move past the header record
'Stop
                    Do Until PatternLn(X, Y) = "End of Pattern"
                        If Len(Trim(PatternLn(X, Y))) <> Len(Trim(!wrktxtline)) Then
                            PatternMatches = False
                        Else
                            If Len(!wrktxtline) > 0 Then
                                For Z = 1 To Len(Trim(PatternLn(X, Y)))
                                    If Mid(PatternLn(X, Y), Z, 1) = Mid(!wrktxtline, Z, 1) Then

                                        PatternMatches = True
                                    ElseIf Mid(PatternLn(X, Y), Z, 1) = "#" And InStr(AlphaStuff & IIf(X = 5, " ", ""), Mid(!wrktxtline, Z, 1)) > 0 Then
                                        PatternMatches = True
                                    Else
                                        PatternMatches = False
                                        Exit For
                                    End If
                                 Next Z
                            Else
                                PatternMatches = True
                            End If
                        End If
                        
                        If PatternMatches Then
                            LineMatches(X, Y) = True
                            Y = Y + 1
                            .MoveNext
                        Else
                            If Y > 1 Then
                                'The following for/next loop is to reset the
                                'txts!wrktxtline back to where the pattern test
                                'begins for the next pattern
                                For Z = Y - 1 To 1 Step -1
                                    .MovePrevious
                                Next Z
                            End If
                                
                            X = X + 1
                            If X > EndX Then Exit Do
                            Y = 1
                        End If
                    Loop
      
    ModLocnMark = "MLC 07"

                    'Step 2, execute the module for the pdf format identified in step 1

                    Forms![HTC200F_G010_F010A Position]!lbl_FilePosition.Caption = !wrktxtfn & " - " & !wrktxtdtrn & " ==> " & ThisFileName & " (" & TxtFormatName(X) & ")"
                    Forms![HTC200F_G010_F010A Position]!lbl_Version.Caption = VersionID
                    Forms![HTC200F_G010_F010A Position].Repaint
'Stop
                    If PatternMatches Then

                        Call Mine_TxtFile(ELThisRun, ELThiseMail, ELThisLineNo, _
                                          ELThisFilePath, ThisSender, _
                                          Val(wCoID), Val(wBrID), TxtFormatName(X), _
                                          wrk_TxtCustomerID, wrk_TxtCustomer, _
                                          wrk_txtHAWB, wrk_txtMAWB, _
                                          wrk_TxtPkupFromID, wrk_TxtPkupFromName, wrk_TxtPkupFromAddress, _
                                          wrk_TxtPkupFromNotes, wrk_TxtPkupDate, wrk_TxtPkuptime, _
                                          wrk_TxtDelToID, wrk_TxtDelToName, wrk_TxtDelToAddress, wrk_TxtDelToNotes, _
                                          wrk_TxtDelDate, wrk_TxtDelTime, wrk_TxtQty, wrk_TxtWeight, wrk_TxtComments, _
                                          wrk_TxtProcessYN)
                                          
                        If TxtFormatHasInfo(X) And wrk_TxtProcessYN Then
                                EachPDF.AddNew
                                        'EachPDF!txtemailhdr = ThisTxtFileName
                                        EachPDF!txtemailhdr = ELThiseMail
                                        EachPDF!txtwhensent = HTC200F_EM_DtTm(ELThisFilePath)
                                        EachPDF!TxtCoID = Val(wCoID)
                                        EachPDF!TxtBrID = Val(wBrID)
                                        EachPDF!txtfilename = ThisFileName
                                        EachPDF!TxtDocType = TxtFormatName(X)
                                        EachPDF!txtcustomerid = wrk_TxtCustomerID
                                        EachPDF!txtCustomer = wrk_TxtCustomer
                                        EachPDF!TxtHAWB = Left(wrk_txtHAWB, 8)
                                        EachPDF!txtMAWB = wrk_txtMAWB
                                        EachPDF!TxtPkupFromID = wrk_TxtPkupFromID

                                        If Len(Trim(wrk_TxtPkupFromName)) > 100 Then wrk_TxtPkupFromName = Trim(Left(wrk_TxtPkupFromName, 100))
                                        EachPDF!TxtPkupFromName = Trim(wrk_TxtPkupFromName)

                                        If Len(Trim(wrk_TxtPkupFromAddress)) > 255 Then wrk_TxtPkupFromAddress = Trim(Left(wrk_TxtPkupFromAddress, 255))
                                        EachPDF!TxtPkupFromAddress = Trim(wrk_TxtPkupFromAddress)

                                        If Len(Trim(wrk_TxtPkupFromNotes)) > 255 Then wrk_TxtPkupFromNotes = Trim(Left(wrk_TxtPkupFromNotes, 255))
                                        EachPDF!TxtPkupFromNotes = Trim(wrk_TxtPkupFromNotes)

                                        EachPDF!TxtPkupDate = wrk_TxtPkupDate
                                        EachPDF!TxtPkupTime = wrk_TxtPkuptime
                                        EachPDF!TxtDelToID = wrk_TxtDelToID

                                        If Len(Trim(wrk_TxtDelToName)) > 100 Then wrk_TxtDelToName = Trim(Left(wrk_TxtDelToName, 100))
                                        EachPDF!TxtDelToName = Trim(wrk_TxtDelToName)

                                        If Len(Trim(wrk_TxtDelToAddress)) > 255 Then wrk_TxtDelToAddress = Trim(Left(wrk_TxtDelToAddress, 255))
                                        EachPDF!TxtDelToAddress = Trim(wrk_TxtDelToAddress)

                                        If Len(Trim(wrk_TxtDelToNotes)) > 255 Then wrk_TxtDelToNotes = Trim(Left(wrk_TxtDelToNotes, 255))
                                        EachPDF!TxtDelToNotes = Trim(wrk_TxtDelToNotes)

                                        EachPDF!TxtDelDate = wrk_TxtDelDate
                                        EachPDF!TxtDeltime = wrk_TxtDelTime
                                        EachPDF!TxtQty = wrk_TxtQty
                                        EachPDF!TxtWeight = wrk_TxtWeight
                                        EachPDF!TxtNotes = wrk_TxtComments
                                        EachPDF!txtprocessyn = wrk_TxtProcessYN
                                        EachPDF!txtaddress = "C:\HTC_Parsed_PDF\" & ThisFileName
                                        EachPDF!pdfaddress = "C:\HTC_EmailToParse\" & Replace(ThisFileName, ".txt", ".pdf")
                                        EachPDF!txtthissender = ThisSender
                                EachPDF.Update
                            
                                ELThisLineNo = ELThisLineNo + 1
                                Logfile.AddNew
                                    Logfile!etolog_thisrun = ELThisRun
                                    Logfile!etolog_emailid = ThisTxtFileName
                                    Logfile!etolog_lineno = ELThisLineNo
                                    Logfile!etolog_filepath = ELThisFilePath
                                    Logfile!etolog_sender = ThisSender
                                    Logfile!etolog_customerid = 0
                                    Logfile!etolog_hawb = wrk_txtHAWB
                                    Logfile!etolog_ordercreated = False
                                    Logfile!etolog_orderno = 0
                                    Logfile!etolog_processedok = True
                                    Logfile!etolog_comment = TxtFormatName(X) & " processed Successfully."
                                Logfile.Update
                        
                        Else  'is defined, but has no order information
                                wrk_TxtProcessYN = True
                                EachPDF.AddNew
                                    EachPDF!txtemailhdr = ELThiseMail
                                    EachPDF!txtwhensent = HTC200F_EM_DtTm(ELThisFilePath)
                                    EachPDF!TxtCoID = Val(wCoID)
                                    EachPDF!TxtBrID = Val(wBrID)
                                    EachPDF!txtfilename = ThisFileName
                                    EachPDF!TxtDocType = TxtFormatName(X)
                                    EachPDF!txtcustomerid = wrk_TxtCustomerID
                                    EachPDF!txtCustomer = wrk_TxtCustomer
                                    EachPDF!TxtNotes = wrk_TxtComments
                                    EachPDF!txtprocessyn = wrk_TxtProcessYN
                                    EachPDF!txtaddress = "C:\HTC_Parsed_PDF\" & ThisFileName
                                    EachPDF!pdfaddress = "C:\HTC_EmailToParse\" & Replace(ThisFileName, ".txt", ".pdf")
                                    EachPDF!txtthissender = ThisSender
                                EachPDF.Update
                                
                                ELThisLineNo = ELThisLineNo + 1
                                 Logfile.AddNew
                                    Logfile!etolog_thisrun = ELThisRun
                                    Logfile!etolog_emailid = ThisTxtFileName
                                    Logfile!etolog_lineno = ELThisLineNo
                                    Logfile!etolog_filepath = ELThisFilePath
                                    Logfile!etolog_sender = ""
                                    Logfile!etolog_customerid = 0
                                    Logfile!etolog_hawb = wrk_txtHAWB
                                    Logfile!etolog_ordercreated = False
                                    Logfile!etolog_orderno = 0
                                    Logfile!etolog_processedok = True
                                    Logfile!etolog_comment = TxtFormatName(X) & " is marked as having no info of value."
                                Logfile.Update
                        End If
                    Else   'Don't know what this document is
                        wrk_TxtProcessYN = False
                        EachPDF.AddNew
                            EachPDF!txtemailhdr = ELThiseMail
                            EachPDF!txtwhensent = HTC200F_EM_DtTm(ELThisFilePath)
                            EachPDF!TxtCoID = Val(wCoID)
                            EachPDF!TxtBrID = Val(wBrID)
                            EachPDF!txtfilename = ThisFileName
                            EachPDF!TxtDocType = TxtFormatName(X)
                            EachPDF!txtcustomerid = wrk_TxtCustomerID
                            EachPDF!txtCustomer = wrk_TxtCustomer
                            EachPDF!TxtNotes = wrk_TxtComments
                            EachPDF!txtprocessyn = wrk_TxtProcessYN
                            EachPDF!txtaddress = "C:\HTC_Parsed_PDF\" & ThisFileName
                            EachPDF!pdfaddress = "C:\HTC_EmailToParse\" & Replace(ThisFileName, ".txt", ".pdf")
                            EachPDF!txtthissender = ThisSender
                        EachPDF.Update
                
                        ELThisLineNo = ELThisLineNo + 1
                        Logfile.AddNew
                            Logfile!etolog_thisrun = ELThisRun
                            Logfile!etolog_emailid = ThisTxtFileName
                            Logfile!etolog_lineno = ELThisLineNo
                            Logfile!etolog_filepath = ELThisFilePath
                            Logfile!etolog_sender = ""
                            Logfile!etolog_customerid = 0
                            Logfile!etolog_hawb = ""
                            Logfile!etolog_ordercreated = False
                            Logfile!etolog_orderno = 0
                            Logfile!etolog_processedok = False
                            Logfile!etolog_comment = "This txt file does not match a defined pattern."
                        Logfile.Update
                    End If
                End With
            Next f

FinishUP:

    ModLocnMark = "MLC 08"

           Call HTC350C_2of2_CreateOrders(ELThisRun, ELThiseMail, ELThisLineNo, VersionID, HAWBProcessed)
    'Stop

    ModLocnMark = "MLC 09"

           Call HTC350C_PurgePDFFiles(ELThisRun, ELThiseMail, ELThisLineNo)

            'Delete the WLI record created when the job started
            '2022-12-08: Since the following process will only delete the first
            '            it finds and the only explanation I can find for a residual
            '            ETO log in is there must be more than one.  So I've changed
            '            the process to delete all ETO instances in the WLI
            '            WhosLoggedIn table.

     ModLocnMark = "MLC 10"

            With WLI
                If Not .EOF Then
                    .MoveFirst
                    Do Until .EOF
                        If !wli_company = Val(wCoID) And _
                           !wli_branch = Val(wBrID) And _
                           !pcname = xPCName And _
                           !pclid = xPCLID And _
                           !wli_staffid = 0 And _
                           !WhosLoggedIn = xWhosLoggedIn Then
                                .Delete
'                                Exit Do
                        End If
                        .MoveNext
                    Loop
                End If
            End With

    ModLocnMark = "MLC 11"
            
            With Forms![HTC200F_G010_F010A Position]
                !lbl_FilePosition.Caption = vbCrLf & "Process complete" & vbCrLf
                !lbl_Version.Caption = VersionID
                .Refresh
                .Repaint
            End With
            
            Call HTC200F_Wait(5)
            
        Application.Quit
'====================================================================
        
ModuleFailed:
'Stop
    'If the module got here with a blank message, then this was an error
    'that's not been dealt with, otherwise a detected error was
          'noted.

     With Logfile
          ELThisLineNo = ELThisLineNo + 1
          .AddNew
              !etolog_coid = wCoID
              !etolog_brid = wBrID
              !etolog_thisrun = ELThisRun
              !etolog_emailid = ELThiseMail
              !etolog_lineno = ELThisLineNo
              !etolog_filepath = ELThisFilePath
              !etolog_sender = ""
              !etolog_customerid = 0
              !etolog_hawb = ""
              !etolog_ordercreated = False
              !etolog_orderno = 0
              !etolog_processedok = False
              If Msg <> "" Then Msg = Msg & "; " & vbCrLf
              Msg = Msg & "Module: " & ModuleName & ": LocationMark:" & ModLocnMark & _
                          ": Line No: " & Erl & _
                          " failed with error " & Err.Number & "; " & Err.Description

              !etolog_comment = Msg
          .Update
      End With

      If InStr(Msg, "A. The first line of the work file is NOT a file header") > 0 Then GoTo FinishUP

      Resume Next

End Sub

Sub Mine_TxtFile(ELThisRun As Date, ELThiseMail As String, ELThisLineNo As Integer, _
                 wThisFileWithPath As String, wThisSender As String, _
                 wCoID As Integer, wBrID As Integer, _
                 wFormatName As String, _
                 wtxtCustomerID As Integer, wtxtCustomer As String, _
                 wtxtHAWB As String, wtxtMAWB As String, _
                 wtxtPkupFromID As Double, _
                 wtxtPkupFromName As String, _
                 wtxtPkupFromAddress As String, _
                 wtxtPkupFromNotes As String, _
                 wtxtPkupDate As String, _
                 wtxtPkupTime As String, _
                 wtxtDelToID As Double, _
                 wtxtDelToName As String, _
                 wtxtDelToAddress As String, _
                 wtxtDelToNotes As String, _
                 wtxtDelDate As String, _
                 wtxtDelTime As String, _
                 wtxtQty As Integer, _
                 wtxtWeight As Integer, _
                 wtxtComments As String, _
                 wtxtProcessYN As Boolean _
                 )
                 
    On Error GoTo Mine_TxtFile_Error
                 
'Stop

'=======================================================================
'===  SOS Routing  =====================================================
'=======================================================================
  
    Dim ModuleName As String: ModuleName = "HTC350C_1of2 Translation/MineTxtFile"
    Dim ModLocnMark As String: ModLocnMark = "Module start"

    If wFormatName = "SOS Routing" Then
    
        Call HTC200F_SOS_Routing(ELThisRun, ELThiseMail, ELThisLineNo, _
                                 wThisFileWithPath, wThisSender, _
                                 wCoID, wBrID, _
                                 wFormatName, _
                                 wtxtCustomerID, wtxtCustomer, _
                                 wtxtHAWB, wtxtMAWB, _
                                 wtxtPkupFromID, _
                                 wtxtPkupFromName, _
                                 wtxtPkupFromAddress, _
                                 wtxtPkupFromNotes, _
                                 wtxtPkupDate, _
                                 wtxtPkupTime, _
                                 wtxtDelToID, _
                                 wtxtDelToName, _
                                 wtxtDelToAddress, _
                                 wtxtDelToNotes, _
                                 wtxtDelDate, _
                                 wtxtDelTime, _
                                 wtxtQty, wtxtWeight, _
                                 wtxtComments, _
                                 wtxtProcessYN)
    
    ElseIf wFormatName = "SOS BOL" Then
    
        Dim Skip2ndLine As Boolean: Skip2ndLine = False
        Dim ExtraCharacterln1 As Boolean: ExtraCharacterln1 = False
        
'5170          Skip2ndLine = False
        Call HTC200F_SOS_BOL(ELThisRun, ELThiseMail, ELThisLineNo, _
                             wThisFileWithPath, wThisSender, _
                             wCoID, wBrID, _
                             wFormatName, _
                             wtxtCustomerID, wtxtCustomer, _
                             wtxtHAWB, wtxtMAWB, _
                             wtxtPkupFromID, _
                             wtxtPkupFromName, _
                             wtxtPkupFromAddress, _
                             wtxtPkupFromNotes, _
                             wtxtPkupDate, _
                             wtxtPkupTime, _
                             wtxtDelToID, _
                             wtxtDelToName, _
                             wtxtDelToAddress, _
                             wtxtDelToNotes, _
                             wtxtDelDate, _
                             wtxtDelTime, _
                             wtxtQty, wtxtWeight, _
                             wtxtComments, _
                             wtxtProcessYN, _
                             Skip2ndLine, _
                             ExtraCharacterln1)
    
    ElseIf wFormatName = "SOS BOL2" Then
    'Stop
    
        Call HTC200F_SOS_BOL2(ELThisRun, ELThiseMail, ELThisLineNo, _
                              wThisFileWithPath, wThisSender, _
                              wCoID, wBrID, _
                              wFormatName, _
                              wtxtCustomerID, wtxtCustomer, _
                              wtxtHAWB, wtxtMAWB, _
                              wtxtPkupFromID, _
                              wtxtPkupFromName, _
                              wtxtPkupFromAddress, _
                              wtxtPkupFromNotes, _
                              wtxtPkupDate, _
                              wtxtPkupTime, _
                              wtxtDelToID, _
                              wtxtDelToName, _
                              wtxtDelToAddress, _
                              wtxtDelToNotes, _
                              wtxtDelDate, _
                              wtxtDelTime, _
                              wtxtQty, wtxtWeight, _
                              wtxtComments, _
                              wtxtProcessYN _
                             )
     
    ElseIf wFormatName = "SOS BOL3" Then
    'Stop
    
        Call HTC200F_SOS_BOL3(ELThisRun, ELThiseMail, ELThisLineNo, _
                              wThisFileWithPath, wThisSender, _
                              wCoID, wBrID, _
                              wFormatName, _
                              wtxtCustomerID, wtxtCustomer, _
                              wtxtHAWB, wtxtMAWB, _
                              wtxtPkupFromID, _
                              wtxtPkupFromName, _
                              wtxtPkupFromAddress, _
                              wtxtPkupFromNotes, _
                              wtxtPkupDate, _
                              wtxtPkupTime, _
                              wtxtDelToID, _
                              wtxtDelToName, _
                              wtxtDelToAddress, _
                              wtxtDelToNotes, _
                              wtxtDelDate, _
                              wtxtDelTime, _
                              wtxtQty, wtxtWeight, _
                              wtxtComments, _
                              wtxtProcessYN _
                             )
                                
    ElseIf wFormatName = "SOS Dlvry Rcpt" Then
    
        Call HTC200F_SOS_Dlvry_Rcpt(ELThisRun, ELThiseMail, ELThisLineNo, _
                                    wThisFileWithPath, wThisSender, _
                                    wCoID, wBrID, _
                                    wFormatName, _
                                    wtxtCustomerID, wtxtCustomer, _
                                    wtxtHAWB, wtxtMAWB, _
                                    wtxtPkupFromID, _
                                    wtxtPkupFromName, _
                                    wtxtPkupFromAddress, _
                                    wtxtPkupFromNotes, _
                                    wtxtPkupDate, _
                                    wtxtPkupTime, _
                                    wtxtDelToID, _
                                    wtxtDelToName, _
                                    wtxtDelToAddress, _
                                    wtxtDelToNotes, _
                                    wtxtDelDate, _
                                    wtxtDelTime, _
                                    wtxtQty, wtxtWeight, _
                                    wtxtComments, _
                                    wtxtProcessYN _
                                     )
        
    ElseIf wFormatName = "SOS Alert" Then
    
        Call HTC200F_SOS_Alert(ELThisRun, ELThiseMail, ELThisLineNo, _
                               wThisFileWithPath, wThisSender, _
                               wCoID, wBrID, _
                               wFormatName, _
                               wtxtCustomerID, wtxtCustomer, _
                               wtxtHAWB, wtxtMAWB, _
                               wtxtPkupFromID, _
                               wtxtPkupFromName, _
                               wtxtPkupFromAddress, _
                               wtxtPkupFromNotes, _
                               wtxtPkupDate, _
                               wtxtPkupTime, _
                               wtxtDelToID, _
                               wtxtDelToName, _
                               wtxtDelToAddress, _
                               wtxtDelToNotes, _
                               wtxtDelDate, _
                               wtxtDelTime, _
                               wtxtQty, wtxtWeight, _
                               wtxtComments, _
                               wtxtProcessYN _
                             )


    ElseIf Left(wFormatName, 8) = "SOS MAWB" Then
    
        Call HTC200F_SOS_MAWB(ELThisRun, ELThiseMail, ELThisLineNo, _
                              wThisFileWithPath, wThisSender, _
                              wCoID, wBrID, _
                              wFormatName, _
                              wtxtCustomerID, wtxtCustomer, _
                              wtxtHAWB, wtxtMAWB, _
                              wtxtPkupFromID, _
                              wtxtPkupFromName, _
                              wtxtPkupFromAddress, _
                              wtxtPkupFromNotes, _
                              wtxtPkupDate, _
                              wtxtPkupTime, _
                              wtxtDelToID, _
                              wtxtDelToName, _
                              wtxtDelToAddress, _
                              wtxtDelToNotes, _
                              wtxtDelDate, _
                              wtxtDelTime, _
                              wtxtQty, wtxtWeight, _
                              wtxtComments, _
                              wtxtProcessYN _
                             )
    
    ElseIf wFormatName = "SOS Forward Air Fast Book" Then
'Stop
        Call HTC200F_FA_FastBook(ELThisRun, ELThiseMail, ELThisLineNo, _
                                 wThisFileWithPath, wThisSender, _
                                 wCoID, wBrID, _
                                 wFormatName, _
                                 wtxtCustomerID, wtxtCustomer, _
                                 wtxtHAWB, wtxtMAWB, _
                                 wtxtPkupFromID, _
                                 wtxtPkupFromName, _
                                 wtxtPkupFromAddress, _
                                 wtxtPkupFromNotes, _
                                 wtxtPkupDate, _
                                 wtxtPkupTime, _
                                 wtxtDelToID, _
                                 wtxtDelToName, _
                                 wtxtDelToAddress, _
                                 wtxtDelToNotes, _
                                 wtxtDelDate, _
                                 wtxtDelTime, _
                                 wtxtQty, wtxtWeight, _
                                 wtxtComments, _
                                 wtxtProcessYN _
                                )

    ElseIf wFormatName = "SOS Battery Advisory 2" Then

        Call HTC200F_SOS_BatteryAdvisory2(ELThisRun, ELThiseMail, ELThisLineNo, _
                                 wThisFileWithPath, wThisSender, _
                                 wCoID, wBrID, _
                                 wFormatName, _
                                 wtxtCustomerID, wtxtCustomer, _
                                 wtxtHAWB, wtxtMAWB, _
                                 wtxtPkupFromID, _
                                 wtxtPkupFromName, _
                                 wtxtPkupFromAddress, _
                                 wtxtPkupFromNotes, _
                                 wtxtPkupDate, _
                                 wtxtPkupTime, _
                                 wtxtDelToID, _
                                 wtxtDelToName, _
                                 wtxtDelToAddress, _
                                 wtxtDelToNotes, _
                                 wtxtDelDate, _
                                 wtxtDelTime, _
                                 wtxtQty, wtxtWeight, _
                                 wtxtComments, _
                                 wtxtProcessYN _
                                )
    
    Else
        Call HTC200F_SOS_No_Format(ELThisRun, ELThiseMail, ELThisLineNo, _
                              wThisFileWithPath, wThisSender, _
                              wCoID, wBrID, _
                              wFormatName, _
                              wtxtCustomerID, wtxtCustomer, _
                              wtxtHAWB, wtxtMAWB, _
                              wtxtPkupFromID, _
                              wtxtPkupFromName, _
                              wtxtPkupFromAddress, _
                              wtxtPkupFromNotes, _
                              wtxtPkupDate, _
                              wtxtPkupTime, _
                              wtxtDelToID, _
                              wtxtDelToName, _
                              wtxtDelToAddress, _
                              wtxtDelToNotes, _
                              wtxtDelDate, _
                              wtxtDelTime, _
                              wtxtQty, wtxtWeight, _
                              wtxtComments, _
                              wtxtProcessYN _
                             )
        
        'wFormatName = "UNKNOWN"
        'Stop
    End If

    
    On Error GoTo 0
    Exit Sub

Mine_TxtFile_Error:

    MsgBox "Error " & Err.Number & " (" & Err.Description & ") in procedure Mine_TxtFile, line " & Erl & "."

Stop

End Sub

Sub prep_AllParsedPDFs(AlertTrigger As String, CoID As String, BrID As String, ELThisLineNbr As Integer, NormalEnd As Boolean)
' ----------------------------------------------------------------
' Copyright © 2018-2023 Thomas F. Crabtree, Jr. All rights reserved
' Procedure Name: prep_AllParsedPDFs
' Purpose: Expand all Alerts with multiple DelRcpts into a series of alerts, each with one DelRecpt
' Procedure Kind: Sub
' Procedure Access: Public
' Author: Tom Crabtree
' Date: 03/27/2023
' Change Log
'
' ----------------------------------------------------------------
'Stop
    On Error GoTo prep_AllParsedPDFs_Error
    
    Dim db As Database: Set db = CurrentDb
    
    Dim APPDFs As Recordset
    Set APPDFs = db.OpenRecordset("HTC200F_G030_Q000B All ParsedPDFs Sorted", dbOpenDynaset)
    
    Dim SvdAlertInfo As Recordset
    Set SvdAlertInfo = db.OpenRecordset("HTC200F_G030_T010 SvdAlertHdrs", dbOpenTable)
    
    Dim AddonParsedPDFS As Recordset
    Set AddonParsedPDFS = db.OpenRecordset("HTC200F_G030_T020 addonParsedpdfs", dbOpenTable)
    
    Dim Logfile As Recordset
    Set Logfile = db.OpenRecordset("HTC350_G800_T010 ETOLog", dbOpenDynaset)
    
    Dim StartLineNbr As Integer
    Dim LineNbr As Integer
    Dim EndLineNbr As Integer
    
    Dim SvdFileHdr As String
    Dim SvdFileEnd As String
    
    Dim SvdAlertPreface As String
    Dim DlvrRcptFlag As String: DlvrRcptFlag = "D E L I V E R Y   R E C E I P T"
    Dim X As Integer
    Dim AddOnStarted As Boolean
    Dim SvdFN As Integer
    Dim SvdLN As Integer
    Dim DTRNbr As Integer
    Dim PDFHdr As Variant      ' bookmark for beginning of current File Number
    Dim PDFTrailer As Variant  ' bookmark last line of current file number
    
    Dim ErrMsg As String

'****** Begin Added 3/22/23 **********************************************
    Dim AtLeastOneDRFound As Boolean: AtLeastOneDRFound = False
    Dim BackToLineNbr As Integer
'******   End Added 3/22/23 **********************************************

    'Objective is to fix any alerts so that if they contain multiple Delivery Receipts, they are
    'split up so that there's one delivery receipt per Alert header. Those txt files that do not
    'match the alert trigger are skipped.

    With APPDFs
        If .RecordCount = 0 Then
            ErrMsg = "There are no PDF's to process, ETO is terminated"
            GoTo prep_AllParsedPDFs_Error
        End If

        'Empty the AddonParsedPDFs table
        If Not AddonParsedPDFS.EOF Then
            AddonParsedPDFS.MoveFirst
            Do Until AddonParsedPDFS.EOF
                AddonParsedPDFS.Delete
                AddonParsedPDFS.MoveNext
            Loop
        End If
  
        'Begin the examination of the pdf table
  
        If Not .EOF Then
            .MoveFirst
            'LineNbr = 0
        End If
      
        If Not .EOF Then
            Do Until .EOF
                ' > the table is read until a File header is read (should be the 1st record)
                ' > when a file header is encountered, its  position and content is saved
                '     for potential use
    
                If Left(!txtline, 13) = "**FileStart**" Then
                    SvdFN = !FN
                    SvdFileHdr = !txtline
                    PDFHdr = .Bookmark
                    DTRNbr = 0
                End If
              
                .MoveNext
             
                ' Check to see if the record read matches the target pattern (AlertTrigger given to the subroutine)
                ' > If so, then we process that txt file from beginning to end, creating one Alert txt file for
                '        each "Delivery Receipt encountered
              '   > If not, the process reads thru the table until it encounters another "**FileStart**"
    
                If Trim(!txtline) = AlertTrigger Then
    'Stop
                    AtLeastOneDRFound = False
                    Do Until Left(!txtline, 11) = "**FileEnd**"
                        .MoveNext
                        If InStr(!txtline, DlvrRcptFlag) > 0 Then AtLeastOneDRFound = True
                        '******   End Added 3/22/23 **********************************************
                    Loop

                     If Not AtLeastOneDRFound Then
                        'Same thing that happens if it's not an alerttrigger.
                        .Bookmark = PDFHdr: .MoveNext   'move to the line AFTER the PDF Header
                        GoTo TheresNoDR
                    End If
                  
                    SvdLN = !LN
                    SvdFileEnd = !txtline
                    PDFTrailer = .Bookmark
                
                    'At this point, I know where the source txt file begins and ends.
                
                    'Copy the AlertHdrs for use with all Delivery Receipts
                    ' added to the APPDFs table
                
                    'Empty the SvdAlertHdrs table from last encounter with an alert pdf
                    If Not SvdAlertInfo.EOF Then
                        SvdAlertInfo.MoveFirst
                        Do Until SvdAlertInfo.EOF
                            SvdAlertInfo.Delete
                            SvdAlertInfo.MoveNext
                        Loop
                    End If
                
                    ' Move back to where the parsed entry begins,
                    ' and copy the lines up to delivery receipt.
                    ' These lines will be put in front of each doc created
                
                    '.MoveFirst
                    .Bookmark = PDFHdr       '.Move StartLineNbr:
                    DTRNbr = DTRNbr + 1
'Stop
                    Do Until Left(!txtline, Len(DlvrRcptFlag)) = DlvrRcptFlag
                        SvdAlertInfo.AddNew
                            SvdAlertInfo!svdalertFN = !FN
                            SvdAlertInfo!svdalertdtrn = DTRNbr
                            SvdAlertInfo!svdalertln = !LN
                            SvdAlertInfo!svdalerthdr = !txtline
                        SvdAlertInfo.Update
                        .MoveNext
                    Loop
               
                    ' I've saved the lines leading up to the Delivery receipt portion
                      
                    'Copy the Delivery Receipt Flag phrase to the AddonParsedPdfs
                    ' Each time I run into the Delivery Receipt flag,
                    '  > copy the file header into the AddonParsed PDFS
                    '  > Copy the saved alert info into the AddonParsed PDFS
                    '  > copy the Delivery Receipt line into the addon parsed pdfs
                    '  > copy each following line into the addon parsed pdfs UNTIL
                    '    FileEnd or another encounter with DlvryRcpt Flag is encountered
                    '  > copy the file trailer into the addon parsed pdfs
                   
                    AddOnStarted = False
                      
                    Do Until Left(!txtline, 11) = "**Fileend**"
                        If Left(!txtline, Len(DlvrRcptFlag)) = DlvrRcptFlag Then
                            'If this is the firsttime DlvrRctpFlag's been encountered then
                            '    there's no need for a file trailer.  If NOT the first time
                            '    for this txt file, then the file trailer is needed to close
                            '    out the add on parsed pdf entry.
                              
                            If AddOnStarted Then
                                AddonParsedPDFS.AddNew
                                    AddonParsedPDFS!FN = SvdFN
                                    AddonParsedPDFS!DTRN = DTRNbr
                                    AddonParsedPDFS!LN = SvdLN
                                    AddonParsedPDFS!addonparsedpdf = SvdFileEnd
                                AddonParsedPDFS.Update
                                DTRNbr = DTRNbr + 1
                            '================================================================
                            '==== I think here I duplicate the pdf and txt files, appending the DTRNnbr to the
                            '==== end of the txtfile I'm about to duplicate.  Needs to be there so it can be
                            '==== added to the 2nd and subsequent orders created from the delivery receipt notice
                            '==================================================================================
                             Else
                                AddOnStarted = True
                            End If
                              
                            'Copy the Alert leading rows to the addon parsed pdf table
                            SvdAlertInfo.MoveFirst
                            Do Until SvdAlertInfo.EOF
                                AddonParsedPDFS.AddNew
                                    AddonParsedPDFS!FN = SvdAlertInfo!svdalertFN
                                    AddonParsedPDFS!DTRN = DTRNbr
                                    AddonParsedPDFS!LN = SvdAlertInfo!svdalertln
                                    AddonParsedPDFS!addonparsedpdf = SvdAlertInfo!svdalerthdr
                                AddonParsedPDFS.Update
                                SvdAlertInfo.MoveNext
                            Loop
                              
                            'Copy the txt line containing the DlvrRcptFlag to to the addon parsed pdf table
                            AddonParsedPDFS.AddNew
                                AddonParsedPDFS!FN = !FN
                                AddonParsedPDFS!DTRN = DTRNbr
                                AddonParsedPDFS!LN = !LN
                                AddonParsedPDFS!addonparsedpdf = !txtline
                            AddonParsedPDFS.Update
                        Else
                            AddonParsedPDFS.AddNew
                                AddonParsedPDFS!FN = !FN
                                AddonParsedPDFS!DTRN = DTRNbr
                                AddonParsedPDFS!LN = !LN
                                AddonParsedPDFS!addonparsedpdf = !txtline
                            AddonParsedPDFS.Update
                        End If
                        .MoveNext
                    Loop
'Stop
                    AddonParsedPDFS.AddNew
                        AddonParsedPDFS!FN = SvdFN
                        AddonParsedPDFS!DTRN = DTRNbr
                        AddonParsedPDFS!LN = SvdLN
                        AddonParsedPDFS!addonparsedpdf = SvdFileEnd
                    AddonParsedPDFS.Update
              
                    SvdAlertInfo.MoveFirst
                    Do Until SvdAlertInfo.EOF
                        SvdAlertInfo.Delete
                        SvdAlertInfo.MoveNext
          
                    Loop
              
                    'mark the original AllParsedPDFs for this alert for deletion
                    .Bookmark = PDFHdr  'Mark the header
                    .Edit
                        !deleterow = True
                    .Update
                    .MoveNext
                    
                    Do Until Left(!txtline, 11) = "**FileEnd**" ' Mark everything after the header
                        .Edit                                   ' and b4 the trailer
                            !deleterow = True
                        .Update
                        .MoveNext
                    Loop
                    .Edit   'Mark the trailer
                        !deleterow = True
                    .Update
                    .MoveNext  'move to next file header or establish .eof
  'Stop
                Else
TheresNoDR:
                    Do Until Left(!txtline, 11) = "**FileEnd**"
                        .MoveNext: LineNbr = LineNbr + 1
                    Loop
                    .MoveNext
                    If Not .EOF Then
                        LineNbr = LineNbr + 1
                    Else
                        Exit Do
                    End If
                End If
            Loop
        Else
            If AddonParsedPDFS.RecordCount > 0 Then
                AddonParsedPDFS.MoveFirst
                Do Until AddonParsedPDFS.EOF
                    .AddNew
                        !FN = AddonParsedPDFS!FN
                        !DTRN = DTRNbr
                        !LN = AddonParsedPDFS!LN
                        !txtline = AddonParsedPDFS!addonparsedpdf
                    .Update
                Loop
            End If
        End If

        'remove the Alerts still existing in the input table
  
        .MoveFirst: LineNbr = 0
        Do Until .EOF
            If !deleterow Then .Delete
            .MoveNext: LineNbr = LineNbr + 1
        Loop
  
        If Not .EOF Then .MoveLast  'position at the end of the current
  
        'Re-add the Alert pdf info

    End With
    
    DoCmd.SetWarnings False
        DoCmd.OpenQuery "HTC200F_G030_Q020 Append AddOnParsedPDFs"
    DoCmd.SetWarnings True
    
    'Make sure there are NO rows with a null !txtline
    
    With APPDFs
        .MoveFirst
        Do Until .EOF
            If IsNull(!txtline) Then
                .Edit
                    !txtline = ""
                .Update
            End If
            .MoveNext
        Loop
    End With
    
    On Error GoTo 0
    NormalEnd = True
    Exit Sub

prep_AllParsedPDFs_Error:

    With Logfile
        ELThisLineNo = ELThisLineNo + 1
        .AddNew
            !etolog_coid = Val(CoID)
            !etolog_brid = Val(BrID)
            !etolog_thisrun = ELThisRun
            !etolog_emailid = Format(Now(), "mm/dd/yyyy; hh:mm:ss")
            !etolog_lineno = ELThisLineNo
            !etolog_filepath = ""
            !etolog_sender = ""
            !etolog_customerid = ""
            !etolog_hawb = ""
            !etolog_ordercreated = False
            !etolog_orderno = 0
            !etolog_processedok = False
            If Msg <> "" Then Msg = Msg & "; " & vbCrLf
            If Err.Number > 0 Then
                Msg = "Error " & Err.Number & " (" & Err.Description & ") in procedure prep_AllParsedPDFs, line " & Erl & "."
            Else
                Msg = ErrMsg
                End If
                !etolog_comment = Msg
            .Update
            NormalEnd = False
        End With

End Sub
