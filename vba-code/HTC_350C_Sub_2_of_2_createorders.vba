    
    'Copyright © 2022-2023 Thomas F. Crabtree, Jr. All rights reserved
    
    Sub HTC350C_2of2_CreateOrders(ELThisRun As Date, ELThiseMail As String, ELThisLineNo As Integer, VersionID As String, HAWBProcessed As Boolean)
    
        On Error GoTo HTC350C_2of2_CreateOrders_Error
    ' ----------------------------------------------------------------
    ' Procedure Name: HTC350C_2of2_CreateOrders
    ' Purpose: Notify dispatch of results, Create ETO Orders and notify sender when
    '           orders are created
    ' Procedure Kind: Sub
    ' Procedure Access: Public
    ' Author: Tom Crabtree
    ' Date: 1/3/2023
    ' Change Log
    '   Version 1.00 01-28-2023
    '   - Add code to insure the order about to be created has legitimate values
    '   - Added error handler
    '   - changed the email msg field ebody from short text to long text
    '   Version 2.00 03-16-2023
    '   - Strengthen 'On Error' procedures
    '   - Create log entries regarding completing orders
    '   - Implement capturing latitude and longitude of pickup/Delivery addresses
    '   Version 2.01 04-06-2023
    '   - added extra lines to the Bld_eMail routine to insure I don't get into a loop
    '     creating blank lines on the email to dispatch.  Not sure why this happens, but it
    '     has twice in the recent past.
    '   Version 2.02 10-02-2023
    '   - Routine blew when the oi_pickupnotes field was null.  Changed the process to
    '     check both the oi_PkupNotes or oi_DelNotes were null; if so the value was made
    '     to be empty (i.e. == "")
    '
    '
    ' ----------------------------------------------------------------
    
    
        Dim db As Database: Set db = CurrentDb
        
        Dim ThisModule As String: ThisModule = "HTC350C_2of2_CreateOrders"
      
        Dim EachTxt As Recordset
        Set EachTxt = db.OpenRecordset("HTC200F_G020_q040 TxtFileNames Sorted", dbOpenDynaset)
        
        Dim HAWBValues As Recordset
        Set HAWBValues = db.OpenRecordset("HTC200F_G020_Q010 Current HAWB values sorted", dbOpenDynaset)
        
        Dim OrderInfo As Recordset
        Set OrderInfo = db.OpenRecordset("HTC200F_G020_T010 Suggested Orders", dbOpenTable)
        
        Dim WorkTable As Recordset
        Set WorkTable = db.OpenRecordset("HTC200F_G020_T000 Work Table", dbOpenTable)
        
        Dim Logfile As Recordset
        Set Logfile = db.OpenRecordset("HTC350_G800_T010 ETOLog", dbOpenDynaset)
        
        Dim FormCount As Integer: FormCount = 8
        Dim FormName(8, 2) As String
        
        Dim X As Integer
        
        Dim eMsg As String
        Dim LocnMarker As String
        Dim ProcessWorkTableOK As Boolean
    'Stop
    
        '*********************************************************************
        '** Many of the data elements used in a new order can come from
        '** multiple forms shown below.  The 1st position identifies the
        '** form and the 2nd position identifies the order in which the forms
        '** are checked for presence of the value.  The target value (eg HAWB)
        '** is drawn from the first form (which contains a valid HAWB; if not
        '** there, the next form is checked, and so on.  NOTE if the value being
        '** sought is one of the note fields, all of the forms can contribute to
        '** the notes.
        '**********************************************************************
        
        FormName(1, 1) = "SOS Routing": FormName(3, 2) = "1"
        FormName(2, 1) = "SOS Alert": FormName(1, 2) = "2"
        FormName(3, 1) = "SOS Dlvry Rcpt": FormName(2, 2) = "3"
        FormName(4, 1) = "SOS BOL": FormName(4, 2) = "4"
        FormName(5, 1) = "SOS BOL2": FormName(5, 2) = "5"
        FormName(6, 1) = "SOS BOL3": FormName(6, 2) = "6"
        FormName(7, 1) = "SOS MAWB": FormName(7, 2) = "7"
        FormName(8, 1) = "SOS Forward Air Fast Book": FormName(8, 2) = "8"
      
        Dim ThisCoID As Integer
        Dim ThisBrID As Integer
        Dim ThisCustomerID As Integer
        Dim ThisHAWB As String
        Dim AtLeastOneFound As Boolean
        Dim ThisEmail As String
        Dim ThisSender As String
        Dim ThisDTTM As String
        Dim ThisSubject As String
        
        Dim FirstRcd As Date
        Dim CID As Integer
        Dim OrderNo As Double
        Dim HAWB As String
        Dim MAWB As String
        Dim PUID As Double
        Dim PUDate As String
        Dim PUStartTime As String
        Dim PUEndTime As String
        Dim PUNotes As String
        Dim DelID As Double
        Dim DelDate As String
        Dim DelStartTime As String
        Dim DelEndTime As String
        Dim DelNotes As String
        Dim Pieces As Integer
        Dim Weight As Integer
        Dim HAWBNotes As String
     
        MsgTitle = "HTC200F_G020_F010 OrderCandidates:On Open"
    
        With Forms![HTC200F_G010_F010A Position]
      !Label3.Caption = "HTC Email to Order, Step 2 of 2"
      !lbl_Version.Caption = VersionID
      !lbl_FilePosition.Caption = ""
      .Refresh
        End With
        
        'empty orderinfo table
        With OrderInfo
      If Not .EOF Then
          .MoveFirst
          Do Until .EOF
              .Delete
              .MoveNext
          Loop
      End If
        End With
        
        'begin building suggested orders
    
        With EachTxt
      .MoveLast
      If .RecordCount = 0 Then
          With Logfile
              ELThisLineNo = ELThisLineNo + 1
              .AddNew
                  !etolog_thisrun = ELThisRun
                  !etolog_thiseMail = ELThiseMail
                  !etolog_lineno = ELThisLineNo
                  !etolog_emailid = "No txt files found"
                  !etolog_processedok = True
                  !etolog_comment = "The TxtFileNames table is empty. " & _
                                 "The import operation is terminated."
              .Update
          End With
          Exit Sub
         'Application.Quit
      End If
      
      'BOF process
      LocnMarker = "BOF Process"
      
      .MoveFirst
      ThisCustomerID = !txtcustomerid
      ThisHAWB = !TxtHAWB
      ThisCoID = !TxtCoID
      ThisBrID = !TxtBrID
      ThisEmail = !txtemailhdr
      ThisSender = !txtthissender
      ThisDTTM = !txtwhensent
    
      'Clear Worktable
      If Not WorkTable.EOF Then
          WorkTable.MoveFirst
          Do Until WorkTable.EOF
              WorkTable.Delete
              WorkTable.MoveNext
          Loop
      End If
    
      'Mainline loop
      LocnMarker = "Mainline Loop"
      
      Do Until .EOF
          With Forms![HTC200F_G010_F010A Position]
              !lbl_FilePosition.Caption = "Processing Subject: " & ThisEmail & "; sent " & ThisDTTM
              !lbl_Version.Caption = VersionID
              .Refresh
          End With
    'Stop
          If !txtcustomerid <> 0 And !TxtHAWB <> "" Then
              
              AtLeastOneFound = True
              WorkTable.AddNew
                  For X = 1 To FormCount
                      If FormName(X, 1) = !TxtDocType Then
                          WorkTable!formseq = FormName(X, 2)
                          Exit For
                      End If
                  Next X
                
                  WorkTable!FormName = !TxtDocType: WorkTable!MAWB_Val = !txtMAWB
                  WorkTable!HAWBNotes_Val = !TxtNotes: WorkTable!Pieces_Val = !TxtQty
                  WorkTable!Weight_Val = !TxtWeight: WorkTable!PkupID_Val = !TxtPkupFromID
                  WorkTable!PkupDate_Val = !TxtPkupDate: WorkTable!PkupTime_Val = !TxtPkupTime
                  WorkTable!PkupNotes_Val = !TxtPkupFromNotes: WorkTable!DelID_Val = !TxtDelToID
                  WorkTable!DelDate_Val = !TxtDelDate:  WorkTable!DelTime_Val = !TxtDeltime
                  WorkTable!DelNotes_Val = !TxtDelToNotes
              WorkTable.Update
              .MoveNext
    'Stop
              If Not .EOF Then
                  If !txtcustomerid <> ThisCustomerID Or !TxtHAWB <> ThisHAWB Or _
                      !TxtCoID <> ThisCoID Or !TxtBrID <> ThisBrID Then
                          LocnMarker = "After processing text files about order " & ThisHAWB
                          Call ProcessWorkTable(MAWB, PUID, PUDate, PUStartTime, PUEndTime, PUNotes, _
                              DelID, DelDate, DelStartTime, DelEndTime, DelNotes, _
                              Pieces, Weight, HAWBNotes, ProcessWorkTableOK)
                          If IsNull(ThisHAWB) Then ThisHAWB = ""
                          If IsNull(PUNotes) Then PUNotes = ""
                          If IsNull(DelNotes) Then DelNotes = ""
                          If IsNull(HAWBNotes) Then HAWBNotes = ""
                          If IsNull(ThisSender) Then ThisSender = ""
                          If IsNull(MAWB) Then MAWB = ""
    
                          OrderInfo.AddNew
                              OrderInfo!OI_email = ThisEmail
                              OrderInfo!oi_dttm = ThisDTTM
                              OrderInfo!OI_CoID = ThisCoID: OrderInfo!OI_BrID = ThisBrID
                              OrderInfo!OI_CustomerID = ThisCustomerID
                              OrderInfo!oi_orderno = GetOrderNo(ThisCustomerID, ThisHAWB)
                            
                              If OrderInfo!oi_orderno = 0 Then
                                  If Len(Trim(ThisHAWB)) <> 8 Or _
                                      PUID = 0 Or _
                                      DelID = 0 Then
                                          OrderInfo!oi_orderno = 99999999
                                  End If
                              End If
                              
                              OrderInfo!oi_hawb = ThisHAWB
                              OrderInfo!OI_MAWB = MAWB: OrderInfo!OI_PkupID = PUID: OrderInfo!OI_PkupDate = PUDate
                              OrderInfo!OI_PkupStartTime = PUStartTime: OrderInfo!OI_PkupEndTime = PUEndTime
                              OrderInfo!oi_pkupnotes = IIf(Len(PUNotes) > 255, Left(PUNotes, 255), PUNotes)
                              OrderInfo!OI_DelID = DelID: OrderInfo!OI_DelDate = DelDate
                              OrderInfo!OI_DelStartTime = DelStartTime: OrderInfo!OI_DelEndTime = DelEndTime
                              OrderInfo!oi_delnotes = IIf(Len(DelNotes) > 255, Left(DelNotes, 255), DelNotes)
                              OrderInfo!OI_Pieces = Pieces: OrderInfo!OI_Weight = Weight
                              OrderInfo!OI_HAWBNotes = HAWBNotes
                              OrderInfo!OI_thissender = ThisSender
                          OrderInfo.Update
    
                          WorkTable.MoveFirst
                          Do Until WorkTable.EOF
                              WorkTable.Delete
                              WorkTable.MoveNext
                          Loop
                          ThisCustomerID = !txtcustomerid
                          ThisHAWB = !TxtHAWB
                          ThisCoID = !TxtCoID
                          ThisBrID = !TxtBrID
                          ThisEmail = !txtemailhdr
                          ThisSender = !txtthissender
                          ThisDTTM = !txtwhensent
                  End If
              Else
                  Call ProcessWorkTable(MAWB, PUID, PUDate, PUStartTime, PUEndTime, PUNotes, _
                                        DelID, DelDate, DelStartTime, DelEndTime, DelNotes, _
                                        Pieces, Weight, HAWBNotes, ProcessWorkTableOK)
                  LocnMarker = "Ready to add order info for " & ThisEmail & "; " & thismawb
            
                  If IsNull(ThisHAWB) Then ThisHAWB = ""
                  If IsNull(PUNotes) Then PUNotes = ""
                  If IsNull(DelNotes) Then DelNotes = ""
                  If IsNull(HAWBNotes) Then HAWBNotes = ""
                  If IsNull(ThisSender) Then ThisSender = ""
                  If IsNull(MAWB) Then MAWB = ""
             
                  OrderInfo.AddNew
                      OrderInfo!OI_email = ThisEmail
                      OrderInfo!oi_dttm = ThisDTTM
                      OrderInfo!OI_CoID = ThisCoID: OrderInfo!OI_BrID = ThisBrID
                      OrderInfo!OI_CustomerID = ThisCustomerID
                      OrderInfo!oi_orderno = GetOrderNo(ThisCustomerID, ThisHAWB)
                      OrderInfo!oi_hawb = ThisHAWB
                      OrderInfo!OI_MAWB = MAWB: OrderInfo!OI_PkupID = PUID: OrderInfo!OI_PkupDate = PUDate
                      OrderInfo!OI_PkupStartTime = PUStartTime: OrderInfo!OI_PkupEndTime = PUEndTime
                      OrderInfo!oi_pkupnotes = Trim(Left(PUNotes, 255)): OrderInfo!OI_DelID = DelID: OrderInfo!OI_DelDate = DelDate
                      OrderInfo!OI_DelStartTime = DelStartTime: OrderInfo!OI_DelEndTime = DelEndTime
                      OrderInfo!oi_delnotes = Trim(Left(DelNotes, 255))
                      OrderInfo!OI_Pieces = Pieces: OrderInfo!OI_Weight = Weight
                      OrderInfo!OI_HAWBNotes = Trim(Left(HAWBNotes, 255))
                      OrderInfo!OI_thissender = ThisSender
                  OrderInfo.Update
        
                  'Clear Worktable
                  If Not WorkTable.EOF Then
                      WorkTable.MoveFirst
                      Do Until WorkTable.EOF
                          WorkTable.Delete
                          WorkTable.MoveNext
                      Loop
                  End If
              End If
          Else
              .MoveNext
              If .EOF Then
                  Exit Do
              Else
                  ThisCustomerID = !txtcustomerid
                  ThisHAWB = !TxtHAWB
                  ThisEmail = !txtemailhdr
                  ThisSender = !txtthissender
                  ThisDTTM = !txtwhensent
              End If
          End If
      Loop
        
      'EOF Process
      LocnMarker = "Ready to bld email and order for HAWB " & ThisHAWB
    
      Call Bld_eMail(ELThisRun, ELThisLineNo) 'builds and sends email to HTC dispatcher
    
      If Not AtLeastOneFound Then
          With Logfile
              ELThisLineNo = ELThisLineNo + 1
              .AddNew
                  !etolog_thisrun = ELThisRun
                  !etolog_lineno = ELThisLineNo
                  !etolog_emailid = "No email of value"
                  !etolog_processedok = True
                  !etolog_hawb = ThisHAWB
                  !etolog_sender = ThisSender
                  !etolog_comment = "There are entries in txt file, but none that contain " & _
                                    "valid values of customer and HAWB. The import operation is terminated."
              .Update
          End With
          Exit Sub
          
      'Application.Quit
      End If
        End With
      
        HAWBProcessed = True
    
        On Error GoTo 0
        Exit Sub
    '=========================================================
HTC350C_2of2_CreateOrders_Error:
    
    'Stop
    'resume next
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
            Msg = Msg & "Module: HTC350C_2of2_CreateOrders failed." & _
                        ": Line No: " & Erl & _
                        " failed with error " & Err.Number & "; " & Err.Description
    
            !etolog_comment = Msg
        .Update
      End With
    
      If Err.Number = 3022 Then
          Resume Next
      Else
          Stop
          Resume Next
      End If
    
    End Sub
        
    Sub ProcessWorkTable( _
                         MAWB As String, _
                         PUID As Double, _
                         PUDate As String, _
                         PUStartTime As String, _
                         PUEndTime As String, _
                         PUNotes As String, _
                         DelID As Double, _
                         DelDate As String, _
                         DelStartTime As String, _
                         DelEndTime As String, _
                         DelNotes As String, _
                         Pieces As Integer, _
                         Weight As Integer, _
                         HAWBNotes As String, _
                         ProcessWorkTableOK As Boolean)
        
        On Error GoTo ProcessWorkTable_Error
        
        Dim LocnMarker As String
    
        MAWB = "": Pieces = 0: Weight = 0: HAWBNotes = ""
        PUID = 0: PUDate = "": PUStartTime = "": PUEndTime = "": PUNotes = ""
        DelID = 0: DelDate = "": DelStartTime = "": DelEndTime = "": DelNotes = ""
        
        Dim db As Database: Set db = CurrentDb
           
        Dim WT As Recordset
        Set WT = db.OpenRecordset("HTC200F_G020_Q030 Worktable Sorted", dbOpenDynaset)
        
        With WT
        
             'MAWB
            .MoveFirst
            Do Until .EOF
                If !MAWB_Val <> "" Then
                    MAWB = !MAWB_Val
                    Exit Do
                End If
                .MoveNext
            Loop
            
            'PUID
            .MoveFirst
            Do Until .EOF
                If !PkupID_Val > 0 Then
                    PUID = !PkupID_Val
                    Exit Do
                End If
                .MoveNext
            Loop
            
            'PUDate
            .MoveFirst
            Do Until .EOF
                If !PkupDate_Val <> "" Then
                    PUDate = !PkupDate_Val
                    Exit Do
                End If
                .MoveNext
            Loop
            
            'PUStartTime and PUEndTime
            .MoveFirst
            Do Until .EOF
                If !PkupTime_Val <> "" Then
                    PUStartTime = Left(!PkupTime_Val, 5)
                    PUEndTime = Right(!PkupTime_Val, 5)
                    Exit Do
                End If
                .MoveNext
            Loop
            
            'PUNotes
            .MoveFirst
            PUNotes = ""
            Do Until .EOF
                If !PkupNotes_Val <> "" Then
                    If PUNotes <> "" Then PUNotes = PUNotes & "; "
                    PUNotes = PUNotes & !PkupNotes_Val
                End If
                .MoveNext
            Loop
                
            'Del ID
            .MoveFirst
            Do Until .EOF
                If !DelID_Val > 0 Then
                    DelID = !DelID_Val
                    Exit Do
                End If
                .MoveNext
            Loop
            
            'Del Date
            .MoveFirst
            Do Until .EOF
                If !DelDate_Val <> "" Then
                    DelDate = !DelDate_Val
                    Exit Do
                End If
                .MoveNext
            Loop
            
            'Del Start Time & End time
            .MoveFirst
            Do Until .EOF
                If !DelTime_Val <> "" Then
                    DelStartTime = Left(!DelTime_Val, 5)
                    DelEndTime = Right(!DelTime_Val, 5)
                    Exit Do
                End If
                .MoveNext
            Loop
            
            'del Notes
            DelNotes = ""
            .MoveFirst
            Do Until .EOF
                If !DelNotes_Val <> "" Then
                    If DelNotes <> "" Then DelNotes = DelNotes & "; "
                    DelNotes = DelNotes & !DelNotes_Val
                End If
                .MoveNext
            Loop
            
            'Pieces
            .MoveFirst
            Do Until .EOF
                If !Pieces_Val <> 0 Then
                    Pieces = !Pieces_Val
                    Exit Do
                End If
                .MoveNext
            Loop
            
            'Weight
            .MoveFirst
            Do Until .EOF
                If !Weight_Val <> 0 Then
                    Weight = !Weight_Val
                    Exit Do
                End If
                .MoveNext
            Loop
            
            'hawb notes
            HAWBNotes = ""
            .MoveFirst
            Do Until .EOF
                If !HAWBNotes_Val <> "" Then
                    If HAWBNotes <> "" Then HAWBNotes = HAWBNotes & "; "
                    HAWBNotes = !HAWBNotes_Val
                End If
                .MoveNext
            Loop
        End With
     
        
        On Error GoTo 0
        Exit Sub
    
ProcessWorkTable_Error:
    
        MsgBox "Error " & Err.Number & " (" & Err.Description & ") in procedure ProcessWorkTable, line " & Erl & "."
        Stop
    End Sub
    
    Function GetOrderNo(CID As Integer, HAWB As String) As Double
        
        Dim Ans As Double: Ans = 0
        
        Dim db As Database: Set db = CurrentDb
        
        Dim HAWBs As Recordset
        Set HAWBs = db.OpenRecordset("HTC200F_G020_Q010 Current HAWB values sorted", dbOpenDynaset)
        
        With HAWBs
            HAWBs.MoveFirst
            Do Until .EOF
                If !hawbcustomerid < CID Then
                    .MoveNext
                ElseIf !hawbcustomerid > CID Then
                    Exit Do
                Else
                    If !existinghawbvalues < HAWB Then
                        .MoveNext
                    ElseIf !existinghawbvalues > HAWB Then
                        Exit Do
                    Else
                        Ans = !hawborder
                        Exit Do
                    End If
                End If
    
            Loop
        End With
                        
        GetOrderNo = Ans
    
    End Function
    
    Sub Bld_eMail(ELThisRun As Date, ELThisLineNo As Integer)
        
        On Error GoTo Bld_eMail_Error
        
        Dim db As Database: Set db = CurrentDb
        
        Dim EmailInfo As Recordset   'contains information for the email report
        Set EmailInfo = db.OpenRecordset("HTC200F_G020_Q010 Suggested Orders Sorted", dbOpenDynaset)
        
        Dim eMailBody As Recordset  'will contain text that will be inserted into the email to the dispatcher(s)
        Set eMailBody = db.OpenRecordset("HTC200F_G020_T020 Outlook Body", dbOpenTable)
        
        Dim LineNo As Integer: LineNo = 0
        Dim NewOrderHdrCreated As Boolean: NewOrderHdrCreated = False
        Dim ExistingOrderHdrCreated As Boolean: ExistingOrderHdrCreated = False
        Dim InsufficientInfoHdrCreated As Boolean: InsufficientInfoHdrCreated = False
        
        Dim NewOrderNo As Double
        Dim PkupNoteLines(5) As String
        Dim DelNoteLines(5) As String
        Dim OrdNoteLines(5) As String
        Dim wrkNotes As String
        Dim wrkNotesLen As Integer
        Dim LeadSpaces As Integer: LeadSpaces = 12
        Dim ThisLineLength As Integer
        Dim ThisOrderType As Integer
        Dim MaxLineLength As Integer: MaxLineLength = 80
        Dim ThisSender As String
        Dim ThisDTTM As String
        Dim ThisEmail As String
        Dim eMailSent As Boolean
        'Dim OrderNoCreated As Double
        
        Dim SendTo As String
        Dim SentTo As String
        
        'empty outlook message table
        With eMailBody
            If Not .EOF Then
                .MoveFirst
                Do Until .EOF
                    .Delete
                    .MoveNext
                Loop
            End If
        End With
    
        With EmailInfo
            If Not .EOF Then
                .MoveFirst
                Do Until .EOF
                    NewOrderNo = !oi_orderno
                    ThisEmail = !OI_email
                    ThisDTTM = !oi_dttm
                    ThisSender = !OI_thissender
                    If NewOrderNo = 0 And _
                        (!OI_CustomerID = 0 Or !OI_PkupID = 0 Or _
                          !OI_DelID = 0 Or Len(Trim(!oi_hawb)) <> 8) Then
                        ThisOrderType = 30
                    ElseIf NewOrderNo = 0 Then
                        ThisOrderType = 10
                    Else
                        ThisOrderType = 20
                    End If
                    
                    If ThisOrderType = 10 And Not NewOrderHdrCreated Then
                        '========== insert new order header if not already done =======
                        NewOrderHdrCreated = True
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = ""
                        eMailBody.Update  '<== inserts blank line
                            
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = String(70, "=")
                        eMailBody.Update
                                                
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = String(25, "=") & " New Orders Created " & String(25, "=")
                        eMailBody.Update '<== Inserts new order header"
                            
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = String(70, "=")
                        eMailBody.Update
                        
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = ""
                        eMailBody.Update  '<== inserts blank line
                    '======== End inserting new order header line =======
                        
                    ElseIf ThisOrderType = 20 And Not ExistingOrderHdrCreated Then
                        ExistingOrderHdrCreated = True
                        '========== insert Existing order header if not already done =======
                        NewOrderHdrCreated = True
                        
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                        eMailBody.Update  '<== inserts blank line
                                
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = String(70, "=")
                        eMailBody.Update
                            
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = String(22, "=") & " Regarding Existing Orders " & String(21, "=")
                        eMailBody.Update '<== Inserts new order header"
                        
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = String(70, "=")
                        eMailBody.Update
                        
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                        eMailBody.Update  '<== inserts blank line
                        '======== End inserting existing order header line =======
                    
                    ElseIf ThisOrderType = 30 And Not InsufficientInfoHdrCreated Then
                        InsufficientInfoHdrCreated = True
                        '========== insert Insufficent data order header if not already done =======
                            
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = ""
                        eMailBody.Update  '<== inserts blank line
                    
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = String(70, "=")
                        eMailBody.Update
                            
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = String(16, "=") & " Insufficient Data to create Order(s) " & String(16, "=")
                        eMailBody.Update '<== Inserts new order header"
                    
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = String(70, "=")
                        eMailBody.Update
                        
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = ""
                        eMailBody.Update  '<== inserts blank line
                        
                        '======== End inserting Insufficent data to create orders if not already done =======
                    End If
                    
                    'Begin processing the order
                    
                    If ThisOrderType = 10 Then
    'Stop
                        Call CreateNewOrder(!OI_CoID, _
                                            !OI_BrID, _
                                            !OI_CustomerID, _
                                            !oi_hawb, !OI_MAWB, _
                                            !OI_PkupID, _
                                            !OI_PkupDate, !OI_PkupStartTime, !OI_PkupEndTime, _
                                            !oi_pkupnotes, _
                                            !OI_DelID, _
                                            !OI_DelDate, !OI_DelStartTime, !OI_DelEndTime, _
                                            !oi_delnotes, _
                                            !OI_Pieces, !OI_Weight, _
                                            !OI_HAWBNotes, _
                                            NewOrderNo, _
                                            ThisSender, _
                                            ELThisRun, ELThisLineNo, _
                                            ThisEmail)
                    End If
    'Stop
                    'email title
    
                    wrkNotes = "Email: " & !oi_dttm & ", " & !OI_email
                    If Len(wrkNotes) > MaxLineLength Then
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = "Email: " & !oi_dttm
                        eMailBody.Update
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = "  " & !OI_email
                        eMailBody.Update
                    Else
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = wrkNotes
                        eMailBody.Update
                    End If
                    
                    'Sender'
                    LineNo = LineNo + 1
                    eMailBody.AddNew
                        eMailBody!drlinetype = ThisOrderType
                        eMailBody!drlineno = LineNo
                        eMailBody!drline = "From:  " & !OI_thissender
                    eMailBody.Update
                    
                    'blank line
                    LineNo = LineNo + 1
                    eMailBody.AddNew
                        eMailBody!drlinetype = ThisOrderType
                        eMailBody!drlineno = LineNo
                        eMailBody!drline = ""
                    eMailBody.Update
                    
                    'order details
                    LineNo = LineNo + 1
                    eMailBody.AddNew
                        eMailBody!drlinetype = ThisOrderType
                        eMailBody!drlineno = LineNo
                        eMailBody!drline = "Order: " & NewOrderNo & ", " & HTC200F_Custinfo(!OI_CoID, !OI_BrID, !OI_CustomerID)
                    eMailBody.Update
                    
                    LineNo = LineNo + 1
                    eMailBody.AddNew
                        eMailBody!drlinetype = ThisOrderType
                        eMailBody!drlineno = LineNo
                        eMailBody!drline = Space(LeadSpaces) & "HAWB: " & !oi_hawb & ", MAWB: " & IIf(!OI_MAWB = "", "????????", !OI_MAWB) & _
                                                                ", Pieces: " & !OI_Pieces & ", Weight: " & !OI_Weight
                    eMailBody.Update
                    
                    'order notes
                    wrkNotes = Trim(!OI_HAWBNotes)
    'Stop
                    If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
                        Do Until wrkNotes = ""
                            If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
                                wrkNotes = Space(LeadSpaces + 10) & Trim(wrkNotes)
                                ThisLineLength = HTC200F_SetLineLength(wrkNotes, MaxLineLength)
                                
                                If Left(wrkNotes, ThisLineLength) = "" Then Exit Do  ' not sure why this is needed
                                
                                LineNo = LineNo + 1
                                eMailBody.AddNew
                                    eMailBody!drlinetype = ThisOrderType
                                    eMailBody!drlineno = LineNo
                                    eMailBody!drline = Left(wrkNotes, ThisLineLength)
                                eMailBody.Update
                                wrkNotes = Trim(Replace(wrkNotes, Left(wrkNotes, ThisLineLength), ""))
                            Else
                                LineNo = LineNo + 1
                                eMailBody.AddNew
                                    eMailBody!drlinetype = ThisOrderType
                                    eMailBody!drlineno = LineNo
                                    eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
                                eMailBody.Update
                                wrkNotes = ""
                            End If
                        Loop
                    Else
                        If wrkNotes <> "" Then
                            LineNo = LineNo + 1
                            eMailBody.AddNew
                                eMailBody!drlinetype = ThisOrderType
                                eMailBody!drlineno = LineNo
                                eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
                            eMailBody.Update
                        End If
                    End If
                    
                    'blank line
                    LineNo = LineNo + 1
                    eMailBody.AddNew
                        eMailBody!drlinetype = ThisOrderType
                        eMailBody!drlineno = LineNo
                        eMailBody!drline = ""
                    eMailBody.Update
                    
                    'pickup date/time
                    LineNo = LineNo + 1
                    eMailBody.AddNew
                        eMailBody!drlinetype = ThisOrderType
                        eMailBody!drlineno = LineNo
                        eMailBody!drline = Space(LeadSpaces) & "Pickup: " & !OI_PkupDate & ", " & !OI_PkupStartTime & " - " & !OI_PkupEndTime
                    eMailBody.Update
      'Stop
                    'pickup location
                    Dim FullAddr As String, AddrName As String, AddrLn1 As String, AddrCity As String
                    Dim AddrLn2 As String, AddrACIID As Integer
                    Dim AddrState As String, AddrZip As String, AddrCountry As String
                    Dim ADDRLat As String, AddrLon As String, AddrCarrierYN As Boolean
                    Dim AddrIntlYN As Boolean, AddrLocalyn As Boolean, AddrBRanchYN As Boolean
                    Dim AddrAssessorials As String
                    
                    Call HTC200F_AddrInfo(!OI_CoID, !OI_BrID, !OI_PkupID, FullAddr, _
                         AddrName, AddrLn1, AddrLn2, AddrCity, AddrState, AddrZip, AddrCountry, _
                         ADDRLat, AddrLon, _
                         AddrACIID, AddrCarrierYN, AddrIntlYN, AddrLocalyn, AddrBRanchYN, AddrAssessorials)
                         
                    wrkNotes = FullAddr
                    If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
                        Do Until wrkNotes = ""
                            If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
                                wrkNotes = Space(LeadSpaces + 10) & wrkNotes
                                ThisLineLength = HTC200F_SetLineLength(wrkNotes, MaxLineLength)
                                
                                If Left(wrkNotes, ThisLineLength) = "" Then Exit Do  ' not sure why this is needed
                                                            
                                LineNo = LineNo + 1
                                eMailBody.AddNew
                                    eMailBody!drlinetype = ThisOrderType
                                    eMailBody!drlineno = LineNo
                                    eMailBody!drline = Left(wrkNotes, ThisLineLength)
                                eMailBody.Update
                                wrkNotes = Replace(wrkNotes, Left(wrkNotes, ThisLineLength), "")
                            Else
                                LineNo = LineNo + 1
                                eMailBody.AddNew
                                    eMailBody!drlinetype = ThisOrderType
                                    eMailBody!drlineno = LineNo
                                    eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
                                eMailBody.Update
                                wrkNotes = ""
                            End If
                        Loop
                    Else
                        If wrkNotes <> "" Then
                            LineNo = LineNo + 1
                            eMailBody.AddNew
                                eMailBody!drlinetype = ThisOrderType
                                eMailBody!drlineno = LineNo
                                eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
                            eMailBody.Update
                        End If
                    End If
    
                                     
                    'Pickup Notes
                    If IsNull(!oi_pkupnotes) Then
                        wrkNotes = ""
                    Else
                        wrkNotes = Trim(!oi_pkupnotes)
                    End If
                    
                    If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
                        Do Until wrkNotes = ""
                            If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
                                wrkNotes = Space(LeadSpaces + 10) & wrkNotes
                                ThisLineLength = HTC200F_SetLineLength(wrkNotes, MaxLineLength)
                                LineNo = LineNo + 1
                                eMailBody.AddNew
                                    eMailBody!drlinetype = ThisOrderType
                                    eMailBody!drlineno = LineNo
                                    eMailBody!drline = Left(wrkNotes, ThisLineLength)
                                eMailBody.Update
                                wrkNotes = Replace(wrkNotes, Left(wrkNotes, ThisLineLength), "")
                            Else
                                
                                If Left(wrkNotes, ThisLineLength) = "" Then Exit Do  ' not sure why this is needed
                                                            
                                LineNo = LineNo + 1
                                eMailBody.AddNew
                                    eMailBody!drlinetype = ThisOrderType
                                    eMailBody!drlineno = LineNo
                                    eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
                                eMailBody.Update
                                wrkNotes = ""
                            End If
                        Loop
                    Else
                        If wrkNotes <> "" Then
                            LineNo = LineNo + 1
                            eMailBody.AddNew
                                eMailBody!drlinetype = ThisOrderType
                                eMailBody!drlineno = LineNo
                                eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
                            eMailBody.Update
                        End If
                    End If
                    
                    'blank line
                    LineNo = LineNo + 1
                    eMailBody.AddNew
                        eMailBody!drlinetype = ThisOrderType
                        eMailBody!drlineno = LineNo
                        eMailBody!drline = ""
                    eMailBody.Update
                    
                    'Delivery date/time
                    LineNo = LineNo + 1
                    eMailBody.AddNew
                        eMailBody!drlinetype = ThisOrderType
                        eMailBody!drlineno = LineNo
                        eMailBody!drline = Space(LeadSpaces) & "Delivery: " & !OI_DelDate & ", " & !OI_DelStartTime & " - " & !OI_DelEndTime
                    eMailBody.Update
                                     
                    'delivery location
                    
                    Call HTC200F_AddrInfo(!OI_CoID, !OI_BrID, !OI_DelID, FullAddr, _
                         AddrName, AddrLn1, AddrLn2, AddrCity, AddrState, AddrZip, AddrCountry, _
                         ADDRLat, AddrLon, AddrACIID, _
                         AddrCarrierYN, AddrIntlYN, AddrLocalyn, AddrBRanchYN, AddrAssessorials)
                         
                    wrkNotes = FullAddr
    
                    If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
                        Do Until wrkNotes = ""
                            If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
                                wrkNotes = Space(LeadSpaces + 10) & wrkNotes
                                ThisLineLength = HTC200F_SetLineLength(wrkNotes, MaxLineLength)
                                
                                If Left(wrkNotes, ThisLineLength) = "" Then Exit Do  ' not sure why this is needed
                                                                                        
                                LineNo = LineNo + 1
                                eMailBody.AddNew
                                    eMailBody!drlinetype = ThisOrderType
                                    eMailBody!drlineno = LineNo
                                    eMailBody!drline = Left(wrkNotes, ThisLineLength)
                                eMailBody.Update
                                wrkNotes = Replace(wrkNotes, Left(wrkNotes, ThisLineLength), "")
                            Else
                                LineNo = LineNo + 1
                                eMailBody.AddNew
                                    eMailBody!drlinetype = ThisOrderType
                                    eMailBody!drlineno = LineNo
                                    eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
                                eMailBody.Update
                                wrkNotes = ""
                            End If
                        Loop
                    Else
                        If wrkNotes <> "" Then
                            LineNo = LineNo + 1
                            eMailBody.AddNew
                                eMailBody!drlinetype = ThisOrderType
                                eMailBody!drlineno = LineNo
                                eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
                            eMailBody.Update
                        End If
                    End If
      
                    'Delivery Notes
                    If IsNull(!oi_delnotes) Then
                        wrkNotes = ""
                    Else
                        wrkNotes = Trim(!oi_delnotes)
                    End If
                    
                    If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
                        Do Until wrkNotes = ""
                            If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
                                wrkNotes = Space(LeadSpaces + 10) & wrkNotes
                                ThisLineLength = HTC200F_SetLineLength(wrkNotes, MaxLineLength)
                                
                                If Left(wrkNotes, ThisLineLength) = "" Then Exit Do  ' not sure why this is needed
                                                                                        
                                LineNo = LineNo + 1
                                eMailBody.AddNew
                                    eMailBody!drlinetype = ThisOrderType
                                    eMailBody!drlineno = LineNo
                                    eMailBody!drline = Left(wrkNotes, ThisLineLength)
                                eMailBody.Update
                                wrkNotes = Replace(wrkNotes, Left(wrkNotes, ThisLineLength), "")
                            Else
                                If wrkNotes <> "" Then
                                    LineNo = LineNo + 1
                                    eMailBody.AddNew
                                        eMailBody!drlinetype = ThisOrderType
                                        eMailBody!drlineno = LineNo
                                        eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
                                    eMailBody.Update
                                    wrkNotes = ""
                                End If
                            End If
                        Loop
                    Else
                        LineNo = LineNo + 1
                        eMailBody.AddNew
                            eMailBody!drlinetype = ThisOrderType
                            eMailBody!drlineno = LineNo
                            eMailBody!drline = Space(LeadSpaces + 10)
                        eMailBody.Update
                    End If
                    
                    'Dash Line
                    LineNo = LineNo + 1
                    eMailBody.AddNew
                        eMailBody!drlinetype = ThisOrderType
                        eMailBody!drlineno = LineNo
                        eMailBody!drline = String(MaxLineLength, "-")
                    eMailBody.Update
                    
                    'blank line
                    LineNo = LineNo + 1
                    eMailBody.AddNew
                        eMailBody!drlinetype = ThisOrderType
                        eMailBody!drlineno = LineNo
                    eMailBody.Update
                    .MoveNext
                Loop
    
            End If
        End With
        
        SendTo = "dispatch@harrahtransportation.com"
        
        If Environ("computername") <> "HARRAHSERVER" Then
            SendTo = "tom.crabtree.2@gmail.com"
        End If
        
        Call EmailDispatcher(1, 1, SendTo, eMailSent, SentTo)
    
        
        On Error GoTo 0
        Exit Sub
    
Bld_eMail_Error:
    
        MsgBox "Error " & Err.Number & " (" & Err.Description & ") in procedure Bld_eMail, line " & Erl & "."
        Stop
    End Sub
    
    Sub CreateNewOrder(sCoID As Integer, _
                       sBrID As Integer, _
                       sCustomerID As Integer, _
                       SHAWB As String, sMAWB As String, _
                       sPkupID As Double, _
                       sPkupDate As String, sPkupStartTime As String, sPkupEndTime As String, _
                       sPkupNotes As String, _
                       sDelID As Double, _
                       sDelDate As String, sDelStartTime As String, sDelEndTime As String, _
                       sDelNotes As String, _
                       sPieces As Integer, sWeight As Integer, _
                       sHAWBNotes As String, _
                       NewOrderNo As Double, _
                       sSender As String, _
                       ELThisRun As Date, ELThisLineNo As Integer, OIThiseMail As String)
                 
        On Error GoTo CreateNewOrder_Error
    ' ----------------------------------------------------------------
    ' Procedure Name: CreateNewOrder
    ' Purpose: Build a new order in HTC along with 1 dim, history recd,
    '          one hawb employed record, and 1 attachment per attachment
    '          in the sponsoring email.
    ' Procedure Kind: Sub
    ' Procedure Access: Public
    ' Author: Tom Crabtree
    ' Date: 1/3/2023
    ' Change Log
    '   Ver 01.0 01/13/2023: Insert edits to intercept the creation of orders that
    '                        have a bad order number, pickup or delivery date, hawb
    '                        pkup id or del id.
    '   Ver 01.1 01/19/2023 16:45 : More cleanup required if a new order isn't created
    '   Ver 02.0 03/16/2023
    '       * lots more work on error detection and actions taken in error procedure
    '       * document the creation of the order
    '       * insure the lat/lng values of pickup and delivery addresses are posted to
    '         the order created.
    ' ----------------------------------------------------------------
    
        Dim db As Database: Set db = CurrentDb
        
        Dim NOrder As Recordset
        Set NOrder = db.OpenRecordset("HTC300_G040_T010A Open Orders", dbOpenDynaset)
        
        Dim NDim As Recordset
        Set NDim = db.OpenRecordset("HTC300_G040_T012A Open Order Dims", dbOpenDynaset)
        
        Dim BranchInfo As Recordset
        Set BranchInfo = db.OpenRecordset("HTC300_G000_T020 Branch Info", dbOpenDynaset)
          
        Dim LastOrderNo As Recordset
        Set LastOrderNo = db.OpenRecordset("HTC300_G040_T000 Last OrderNo Assigned", dbOpenDynaset)
        
        Dim OrdersInWork As Recordset
        Set OrdersInWork = db.OpenRecordset("HTC300_G040_T005 Orders In Work", dbOpenDynaset)
        
        Dim Logfile As Recordset
        Set Logfile = db.OpenRecordset("HTC350_G800_T010 ETOLog", dbOpenDynaset)
    
        Dim DocStorage As String
        Dim DocSource As String
        Dim PDFDocPath As String
        
        BranchInfo.MoveFirst   ' There's always exactly one row in this table
        DocStorage = BranchInfo!brdocstoragelocn
        DocSource = "C:\HTC_EmailToParse"
        
        Dim PDFs As Recordset
        Set PDFs = db.OpenRecordset("HTC200F_TxtFileNames", dbOpenTable)
        
        Dim Attachments As Recordset
        Set Attachments = db.OpenRecordset("HTC300_G040_T014A Open Order Attachments", dbOpenDynaset)
        
        Dim Hist As Recordset
        Set Hist = db.OpenRecordset("HTC300_G040_T030 Orders Update History", dbOpenDynaset)
        
    ' Get next order number, & post to OIW
    
    
        NewOrderNo = HTC200F_NextOrderNo(sCoID, sBrID) 'adds 1 to last ordernumber assigned
                                    'Checks the new order number against OIW
                                    'If not currently in work
                                    '   new order number becomes LON and OIW is updated
                                    'else
                                    '   new order number is incremented and checked until
                                    '   it's not found in OIW, after which the latest
                                    '   new order number is assigned LON and OIW is updated.
      
      'get address information for both pickup and delivery addresses
      
        Dim wrkOrderType As Integer
        
        Dim wrkCusName As String, wrkCusTariff As String
        Dim wrkCusQBID As String, wrkCusQBName As String
        Dim wrkCusAssessorials As String
        
        Dim wrkPUFullAddr As String
        Dim wrkPUAddrname As String, wrkPUAddrLn1 As String, wrkPUAddrLn2 As String, wrkPUAddrCity As String
        Dim wrkPUAddrState As String, wrkPUAddrZip As String, wrkPUCountry As String
        Dim wrkPULat As String, wrkPULon As String
        Dim wrkPUACIID As Integer, wrkPUCarrierYN As Boolean, wrkPUAssessorials As String
        Dim wrkPUAddrCarrierYN As Boolean, wrkPUIntlYN As Boolean, wrkPULocalYN As Boolean, wrkPUBranchYn As Boolean
        
        Dim wrkDelFullAddr As String
        Dim wrkDelAddrname As String, wrkDelAddrLn1 As String, wrkDelAddrLn2 As String, wrkDelAddrCity As String
        Dim wrkDelAddrState As String, wrkDelAddrZip As String, wrkDelCountry As String
        Dim wrkDelLat As String, wrkDelLon As String
        Dim wrkdelACIID As Integer, wrkDelCarrierYN As Boolean, wrkDelAssessorials As String
        Dim wrkDelAddrCarrierYN As Boolean, wrkDelIntlYN As Boolean, wrkDelLocalYN As Boolean, wrkDelBranchYn As Boolean
        Dim wrkAssessorial As String
        
        Dim wrkPUACI As String, wrkDelACI As String
        
        Dim wrkEMSubject As String
        
        Dim PDFFileName As String
        Dim AttachCount As Integer
        Dim Svd_Status As String, Svd_StatSeq As Integer
        
        Dim FileStoreOK As Boolean
        
        Dim ENbr As Integer, EDesc As String, LastPDFStoredThisOrder As String
        
        Dim exMsg As String: exMsg = ""
            
        Dim OrderCreated As Boolean: OrderCreated = False
        Dim DimCreated As Boolean: DimCreated = False
        Dim HistCreated As Boolean: HistCreated = False
        Dim CustHAWBCreated As Boolean: CustHAWBCreated = False
        Dim LonUpdated As Boolean: LONumberUpdated = False
        Dim AttachmentMade As Boolean: AttachmentMade = False
        Dim OIWUpdated As Boolean: OIWUpdated = False
        Dim eMailSent As Boolean: eMailSent = False
        Dim SentTo As String
        
        Dim StdStartTime As String: StdStartTime = "09:00"
        Dim StdEndTime As String: StdEndTime = "17:00"
        Dim AbortOrder As Boolean: AbortOrder = False
        
        Dim DfltAgent As Integer: DfltAgent = 159  '<====== when time permits, go get the appropriate default agent
        
        Call HTC200_GetCusName(sCoID, sBrID, sCustomerID, wrkCusName, wrkCusTariff, wrkCusQBID, wrkCusQBName, wrkCusAssessorials)
    
        Call HTC200F_AddrInfo(sCoID, sBrID, sPkupID, wrkPUFullAddr, _
             wrkPUAddrname, wrkPUAddrLn1, wrkPUAddrLn2, wrkPUAddrCity, wrkPUAddrState, _
             wrkPUAddrZip, wrkPUCountry, wrkPULat, wrkPULon, wrkPUACIID, _
             wrkPUCarrierYN, wrkPUIntlYN, wrkPULocalYN, wrkPUBranchYn, wrkAssessorial)
        
        wrkPUACI = HTC200_GetACIArea(wrkPUACIID)
    
        Call HTC200F_AddrInfo(sCoID, sBrID, sDelID, wrkDelFullAddr, _
             wrkDelAddrname, wrkDelAddrLn1, wrkDelAddrLn2, wrkDelAddrCity, wrkDelAddrState, _
             wrkDelAddrZip, wrkDelCountry, wrkDelLat, wrkDelLon, wrkdelACIID, _
             wrkDelCarrierYN, wrkDelIntlYN, wrkDelLocalYN, wrkDelBranchYn, wrkAssessorial)
             
        wrkDelACI = HTC200_GetACIArea(wrkdelACIID)
        '=========================================================================================
        
        wrkOrderType = HTC200F_SetOrderType(wrkPUACI, wrkPUBranchYn, wrkPUCarrierYN, _
                                           wrkDelACI, wrkDelBranchYn, wrkDelCarrierYN)
    'Stop
    '=============================== Audit order about to be created =======================
        
        If Not (IsDate(sPkupDate)) Then
            If Msg <> "" Then exMsg = exMsg & "; "
            exMsg = exMsg & "Bad Pkup Date (" & sPkupDate & "). "
            exMsg = exMsg & " Set to next business day (" & DateAdd("d", 1, Date) & ")"
            sPkupDate = DateAdd("d", 1, Date)
        End If
        
        If Len(Trim(sPkupStartTime)) = 5 Then
            If Not IsNumeric(Left(sPkupStartTime, 2)) Or _
               Not IsNumeric(Right(sPkupStartTime, 2)) Or _
               Mid(sPkupStartTime, 3, 1) <> ":" Then
                  If exMsg <> "" Then exMsg = exMsg & "; "
                  exMsg = exMsg & "Invalid pickup start time (" & sPkupStartTime & "). "
                  exMsg = exMsg & "Standard start time (" & StdStartTime & ") used."
                  sPkupStartTime = StdStartTime
            End If
        Else
            If exMsg <> "" Then exMsg = exMsg & "; "
            exMsg = exMsg & "Invalid pickup time (" & sPkupStartTime & ").  "
            exMsg = exMsg & "Standard start time (" & StdStartTime & ") used."
            sPkupStartTime = StdStartTime
        End If
        
        If Len(Trim(sPkupEndTime)) = 5 Then
            If Not IsNumeric(Left(sPkupEndTime, 2)) Or _
               Not IsNumeric(Right(sPkupEndTime, 2)) Or _
               Mid(sPkupEndTime, 3, 1) <> ":" Then
                  If exMsg <> "" Then exMsg = exMsg & "; "
                  exMsg = exMsg & "Invalid pickup end time (" & sPkupEndTime & "). "
                  exMsg = exMsg & "Default end time (" & StdEndTime & ") used."
                  sPkupEndTime = StdEndTime
            End If
        Else
            If exMsg <> "" Then exMsg = exMsg & "; "
            exMsg = exMsg & "Invalid pickup time (" & sPkupEndTime & "). "
            exMsg = exMsg & "Default End Time (" & StdEndTime & ") used."
            sPkupEndTime = StdEndTime
        End If
        
        If Not (IsDate(sDelDate)) Then
            If Msg <> "" Then exMsg = exMsg & "; "
            exMsg = exMsg & "Bad Delivery Date (" & sDelDate & "). "
            exMsg = exMsg & "Day after pickup date (" & DateAdd("d", 1, sPkupDate) & ") used."
            sDelDate = DateAdd("d", 1, sPkupDate)
        End If
    
        If Len(Trim(sDelStartTime)) = 5 Then
            If Not IsNumeric(Left(sDelStartTime, 2)) Or _
               Not IsNumeric(Right(sDelStartTime, 2)) Or _
               Mid(sDelStartTime, 3, 1) <> ":" Then
                  If exMsg <> "" Then exMsg = exMsg & "; "
                  exMsg = exMsg & "Invalid pickup start time (" & sDelStartTime & "). "
                  exMsg = exMsg & "Standard start time (" & StdStartTime & " used."
            End If
        Else
            If exMsg <> "" Then exMsg = exMsg & "; "
            exMsg = exMsg & "Invalid pickup start time (" & sDelStartTime & "). "
            exMsg = exMsg & "Standard start time (" & StdStartTime & " used."
        End If
    
        If Len(Trim(sDelEndTime)) = 5 Then
            If Not IsNumeric(Left(sDelEndTime, 2)) Or _
               Not IsNumeric(Right(sDelEndTime, 2)) Or _
               Mid(sDelEndTime, 3, 1) <> ":" Then
                  If exMsg <> "" Then exMsg = exMsg & "; "
                  exMsg = exMsg & "Invalid pickup end time (" & sDelEndTime & "). "
                  exMsg = exMsg & "Standard end time (" & StdEndTime & ") used."
                  sDelEndTime = StdEndTime
            End If
        Else
            If exMsg <> "" Then exMsg = exMsg & "; "
            exMsg = exMsg & "Invalid pickup end time (" & sDelEndTime & "). "
            exMsg = exMsg & "Standard end time (" & StdEndTime & ") used."
            sDelEndTime = StdEndTime
        End If
        
        ' Build and insert new order(status 35-ETO Generated)
        OrderCreated = False: DimCreated = False: HistCreated = False
        CustHAWBCreated = False: LonUpdated = False: AttachmentMade = False
        OIWUpdated = False: eMailSent = False: SentTo = ""
        
        With NOrder
            NOrder.AddNew
                !M_COID = sCoID
                !M_BrID = sBrID
                !m_Orderno = NewOrderNo
                !M_OrderType = wrkOrderType
                !m_customerid = sCustomerID
                !m_customer = wrkCusName
                !M_CustAgent = DfltAgent              ' SOS Agent 159 is SOS default agent
                !m_Tariff = wrkCusTariff
                !M_CustAssessorials = wrkCusAssessorials
                !M_HAWB = Trim(SHAWB)
                !M_MAWB = sMAWB
                !M_ProNbr = ""
                !M_OrderNotes = sHAWBNotes
                !M_PUDate = sPkupDate
                
                !M_PUTimeStart = sPkupStartTime
                !M_PUTimeEnd = sPkupEndTime
                !M_DelDate = sDelDate
                !M_DelTimeStart = sDelStartTime
                !M_DelTimeEnd = sDelEndTime
                !M_DeclaredValue = 0
                !m_StorageChgs = 0
                
                !M_PUID = sPkupID
                !M_PUCo = wrkPUAddrname
                !M_PULocn = wrkPUAddrLn1 & ", " & IIf(Len(wrkPUAddrLn2) > 0, wrkPUAddrLn2 & ", ", "") & _
                            wrkPUAddrCity & ", " & wrkPUAddrState & ", " & wrkPUCountry
                !M_PUZip = wrkPUAddrZip
                !m_pulatitude = wrkPULat
                !m_pulongitude = wrkPULon
                If Len(wrkPUACI) > 1 Then wrkPUACI = Left(Trim(wrkPUACI), 1)
                !M_PUACI = wrkPUACI
                !M_PUAssessorials = wrkPUAssessorials
                !M_PUContactName = ""
                !M_PUContactMeans = ""
                !M_PUNotes = sPkupNotes
                !M_PUCarrierYN = wrkPUCarrierYN
                !M_PUIntlYN = wrkPUIntlYN
                !M_PULocalYN = wrkPULocalYN
                !M_PUBranchYN = wrkPUBranchYn
                !M_DelID = sDelID
                !M_DelCo = wrkDelAddrname
                !M_DelLocn = wrkDelAddrLn1 & ", " & IIf(Len(wrkDelAddrLn2) > 0, wrkDelAddrLn2 & ", ", "") & _
                             wrkDelAddrCity & ", " & wrkDelAddrState & ", " & wrkDelCountry
                !M_DelZip = wrkDelAddrZip
                !m_dellatitude = wrkDelLat
                !m_dellongitude = wrkDelLon
                If Len(wrkDelACI) > 1 Then wrkDelACI = Left(Trim(wrkDelACI), 1)
                !M_DelACI = wrkDelACI
                !M_Del_Assessorials = 0
                !M_DelContactName = ""
                !M_DelContactMeans = ""
                !M_DelNotes = sDelNotes
                !M_DelCarrierYN = wrkDelCarrierYN
                !M_DelIntlYN = wrkDelIntlYN
                !M_DelLocalYN = wrkDelLocalYN
                !M_DelBranchYN = wrkDelBranchYn
                !M_PODSig = ""
                !M_PODDate = ""
                !M_PODTime = ""
                !M_PODNotes = ""
                !m_status = "ETO Generated": Svd_Status = !m_status
                !m_statseq = 35: Svd_StatSeq = !m_statseq
                !m_rate = 0
                !m_fsc = 0
                !m_services = 0
                !m_StorageChgs = 0
                !m_adjustments = 0
                !M_RatingNotes = 0
                !M_Charges = !m_rate + !m_fsc + !m_services + !m_adjustments + !m_StorageChgs
                !M_Costs = 0
                !M_QBCustomerListID = wrkCusQBID
                !M_QBCustFullName = wrkCusQBName
                !M_QBInvoiceRefNumber = ""
                !M_AutoAssessYN = False
                !M_WgtChgsCalcYN = False
            .Update
            OrderCreated = True
        End With
      'Stop
        If OrderCreated Then
            ' Build and insert new dim
            With NDim
                .AddNew
                    !od_coid = sCoID
                    !od_brid = sBrID
                    !od_orderno = NewOrderNo
                    !od_dimid = 1
                    !od_unittype = "EA"
                    !od_unitqty = sPieces
                    !od_unitheight = 1
                    !od_unitlength = 1
                    !od_Unitwidth = 1
                    !od_unitweight = sWeight
                    !od_unitdimweight = 0
                .Update
                DimCreated = True
            End With
        End If
      'Stop
        If OrderCreated Then
            LastPDFStoredThisOrder = ""
            With PDFs
                .MoveFirst
                AttachCount = 0
                Do Until .EOF
                    If !txtemailhdr = OIThiseMail And _
                        !pdfaddress <> LastPDFStoredThisOrder And _
                        !txtcustomerid <> 0 Then
                            PDFFileName = Replace(!pdfaddress, "C:\HTC_EmailToParse\", "")
                            Call HTC200_StoreAttachment(DocSource & "\" & PDFFileName, _
                                                        DocStorage, _
                                                        sCoID, _
                                                        sBrID, _
                                                        sCustomerID, _
                                                        NewOrderNo, _
                                                        PDFFileName, _
                                                        PDFDocPath, _
                                                        FileStoreOK, _
                                                        ELThisRun, _
                                                        OIThiseMail, _
                                                        ELThisLineNo, _
                                                        sSender, _
                                                        SHAWB)
                            If FileStoreOK Then
                                Attachments.AddNew
                                    Attachments!att_coid = sCoID
                                    Attachments!att_brid = sBrID
                                    Attachments!att_orderno = NewOrderNo
                                    Attachments!att_custid = sCustomerID
                                    Attachments!att_path = PDFDocPath
                                    Attachments!att_size = FileLen(PDFDocPath) / 1024
                                Attachments.Update
                                LastPDFStoredThisOrder = !pdfaddress
                                AttachCount = AttachCount + 1
                            End If
                    End If
                    .MoveNext
                Loop
            End With
        'Stop
            If AttachCount > 0 Then AttachmentMade = True
        
        End If
    
    'If SHAWB = "WP140834" Then Stop
    
        If OrderCreated Then
            ' post to Last Order Number; Remove oiw entry
            Call HTC200_PosttoLON(sCoID, sBrID, NewOrderNo, LonUpdated)
            Call HTC200_RemoveOIW(sCoID, sBrID, NewOrderNo, OIWUpdated)
        End If
        
        '==================================================
        If OrderCreated Then
            'Try to save the customer/hawb value.
            'In certain cases, reusing the Customer/HAWB value is OK, hence the 'on error' action
    
            On Error GoTo 0
                If Len(Trim(SHAWB)) > 0 Then
                   Dim UsedHAWBs As Recordset
                   Set UsedHAWBs = db.OpenRecordset("HTC300_G040_T040 HAWB Values", dbOpenDynaset)
                   
                   On Error Resume Next
                        With UsedHAWBs
                             .AddNew
                                 !existinghawbvalues = SHAWB
                                 !hawbcoid = sCoID
                                 !hawbbrid = sBrID
                                 !hawbcustomerid = sCustomerID
                                 !hawborder = NewOrderNo
                             .Update
                            .Close
                         End With
                   On Error GoTo CreateNewOrder_Error
                   CustHAWBCreated = True
                End If
        End If
        '==================================================
        If OrderCreated Then
        
            ' Build and insert history
            With Hist
                .AddNew
                    !Orders_UpdtDate = Now()
                    !Orders_UpdtLID = "HarrahServer ETO"
                    !Orders_CoID = sCoID
                    !Orders_BrID = sBrID
                    !Orders_OrderNbr = NewOrderNo
                    !Orders_Changes = "Order #" & NewOrderNo & " Customer: " & wrkCusName & " (#" & _
                                      sCustomerID & ") Created with 1 Dim, " & _
                                                "0 Assessorials, 0 Drivers, and " & AttachCount & " Attachments, assigned " & _
                                                FormatCurrency(0) & " using the " & wrkCusTariff & " tariff; " & _
                                                "Status = " & Svd_Status & "(" & Svd_StatSeq & ") & From eMail rec'd " & _
                                                sDtTm & ", " & OIThiseMail
                .Update
                HistCreated = True
            End With
        End If
    
        If OrderCreated Then
            If sSender <> "" Then
                wrkEMSubject = "Regarding your email dated " & Trim(sDtTm) & vbCrLf & "Subject " & _
                        sSubject & vbCrLf & vbCrLf & " Concerning MAWB: " & IIf(sMAWB = "", "????????", sMAWB) _
                         & "  HAWB: " & SHAWB & vbCrLf & vbCrLf & "HTC order number " & NewOrderNo & " has been created " & _
                         "and forwarded to dispatch." & vbCrLf & vbCrLf & "Thank you for your business."
            'Test Test Test
                If Environ("computername") <> "HARRAHSERVER" Then
                    sSender = "tom.crabtree.2@gmail.com"
                End If
            'Test Test Test
    'Stop
                Call HTC350C_SendEmail("Dispatch@HarrahTransportation.com", _
                                       sSender, _
                                       "Auto Response from Harrah Transportation", _
                                       wrkEMSubject, eMailSent, SentTo)
            End If
        End If
        
        '  =========== Let's see if all really went OK
        Dim ActionArray As String: ActionArray = "........"
        If OrderCreated Then Mid(ActionArray, 1, 1) = "X"
        If DimCreated Then Mid(ActionArray, 2, 1) = "X"
        If HistCreated Then Mid(ActionArray, 3, 1) = "X"
        If CustHAWBCreated Then Mid(ActionArray, 4, 1) = "X"
        If LonUpdated Then Mid(ActionArray, 5, 1) = "X"
        If AttachmentMade Then Mid(ActionArray, 6, 1) = "X"
        If OIWUpdated Then Mid(ActionArray, 7, 1) = "X"
        If eMailSent Then Mid(ActionArray, 8, 1) = "X"
        
        Dim wCmt As String
        'Stop
        With Logfile
            ELThisLineNo = ELThisLineNo + 1
            .AddNew
                !etolog_coid = sCoID
                !etolog_brid = sBrID
                !etolog_thisrun = ELThisRun
                !etolog_emailid = OIThiseMail
                !etolog_lineno = ELThisLineNo
                !etolog_filepath = ""
                !etolog_sender = sSender
                !etolog_customerid = sCustomerID
                !etolog_hawb = SHAWB
                !etolog_orderno = NewOrderNo
      'Stop
                If ActionArray = "XXXXXXXX" Then
                    !etolog_processedok = True
                    !etolog_ordercreated = True
                    !etolog_comment = "Order = " & NewOrderNo & " created and email sent to " & SentTo
                Else
    
                    !etolog_processedok = False
                    !etolog_ordercreated = False
                    wCmt = ""
                    
                    If Not OrderCreated Then
                        If wCmt <> "" Then wCmt = wCmt & "; "
                        wCmt = wCmt & "The order wasn't created."
                    End If
                    
                    If OrderCreated Then
                        If Not DimCreated Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order was created, dim was not" & vbCrLf
                        End If
                        
                        If Not HistCreated Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order was created, History was not" & vbCrLf
                        End If
                         
                        If Not CustHAWBCreated Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order was created, HAWB duplication was not" & vbCrLf
                        End If
                        
                        If Not LonUpdated Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order was created, Last Order number created was not" & vbCrLf
                        End If
                        
                        If Not OIWUpdated Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order was created, Orders in work was not updated" & vbCrLf
                        End If
                        
                        If Not AttachmentMade Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order was created, no attachments were added" & vbCrLf
                        End If
                        
                        If Not eMailSent Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order was created, an eMail to the customer was not sent" & vbCrLf
                        End If
                    Else
                        If DimCreated Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order wasn't created but Dim was," & vbCrLf
                        End If
                        
                        If HistCreated Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order wasn't created but History was." & vbCrLf
                        End If
                         
                        If CustHAWBCreated Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order wasn't created, HAWB duplication was." & vbCrLf
                        End If
                        
                        If LonUpdated Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order wasn't created, Last Order number created was." & vbCrLf
                        End If
                        
                        If OIWUpdated Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order was created, Orders in work was updated." & vbCrLf
                        End If
                        
                        If AttachmentMade Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order wasn't created but attachments were added" & vbCrLf
                        End If
                        
                        If eMailSent Then
                            If wCmt <> "" Then wCmt = wCmt & "; "
                            wCmt = wCmt & "Order was created but an eMail to the customer was sent" & vbCrLf
                        End If
                    End If
                    !etolog_comment = wCmt
                End If
            .Update
    
        End With
        
        Exit Sub
    
CreateNewOrder_Error:
    
        MsgBox "Error " & Err.Number & " (" & Err.Description & ") in procedure CreateNewOrder, line " & Erl & "."
      'Stop
        With Logfile
            ELThisLineNo = ELThisLineNo + 1
            .AddNew
                !etolog_coid = sCoID
                !etolog_brid = sBrID
                !etolog_thisrun = ELThisRun
                !etolog_emailid = OIThiseMail
                !etolog_lineno = ELThisLineNo
                !etolog_filepath = ""
                !etolog_sender = ""
                !etolog_customerid = 0
                !etolog_hawb = ""
                !etolog_ordercreated = False
                !etolog_orderno = 0
                !etolog_processedok = False
                !etolog_comment = "Module: " & ModuleName & ": LocationMark:" & ModLocnMark & _
                            ": Line No: " & Erl & _
                            " failed with error " & Err.Number & "; " & Err.Description
            .Update
        End With
        
        If AbortOrder Or (Err.Number > 0 And Err.Number <> 3022) Then '
            Stop
            Resume Next
        Else
            Resume Next
        End If
        
    End Sub
    
    Sub EmailDispatcher(sCoID As Integer, sBrID As Integer, SendToAddress As String, eMailSent As Boolean, Sent As String)
    
        On Error GoTo EmailDispatcher_Error
        Dim db As Database: Set db = CurrentDb
        
        Dim MsgLines As Recordset
        Set MsgLines = db.OpenRecordset("Htc200F_G020_Q060 Outlook Body Sorted", dbOpenDynaset)
        
        Dim eMsubject As String
        Dim eMbody As String
        Dim eEditable As Boolean: eEditable = False
        Dim SentTo As String
        
        eMsubject = "Automated eMail Order Processing"
        
        eMbody = ""
        
        If MsgLines.RecordCount > 0 Then
            
            MsgLines.MoveFirst
            Do Until MsgLines.EOF
                eMbody = eMbody & MsgLines!drline & vbCrLf
                MsgLines.MoveNext
            Loop
    
    'Stop
    'Test Test Test
            If Environ("computername") <> "HARRAHSERVER" Then
                SendToAddress = "tom.crabtree.2@gmail.com"
            End If
    'Test Test Test
    
            Call HTC350C_SendEmail("alert@HarrahTransportation.com", _
                                   SendToAddress, _
                                   eMsubject, _
                                   eMbody, _
                                   eMailSent, _
                                   SentTo)
                                   
                    'sFrom As String, _
                    'sSendTo As String, _
                    'sSubject As String, _
                    'sBody As String, _
                    'seMailSent As Boolean, _
                    'sSentTo As String
                                   
        End If
        
        
        On Error GoTo 0
        Exit Sub
    
EmailDispatcher_Error:
    
        MsgBox "Error " & Err.Number & " (" & Err.Description & ") in procedure EmailDispatcher, line " & Erl & "."
        Stop
    End Sub
    
    'Note: HTC200F_SetOrderType is a mod of the HTC200_SetOrderType in the HTC_Modules dtabase
    
    Function HTC200F_SetOrderType(PUACI As String, PUBranchYN As Boolean, PUCarrier As Boolean, _
                                    DelACI As String, DelBranchYN As Boolean, DelCarrier As Boolean) As Integer
    
        Dim db As Database
        Set db = CurrentDb
        
        Dim LowACI As String
        Dim HighACI As String
        
        Dim FAns As Integer
        
        'LowACI = "A"
        'HighACI = "D"
        
        ' 1 - Recovery,  2 - Drop,    3 - Point-to-Point, 4 - Hot Shot, 5 - Dock Transfer
        ' 6 - Services,  7 - Storage, 8 - Transfer,       9 - Pickup,  10 - Delivery
        
    'Stop
        
        'Get high/low ACI for branch
            Dim Branch As Recordset
            Set Branch = db.OpenRecordset("HTC300_G000_T020 Branch Info", dbOpenDynaset)
                    
            Dim wrkBrACILow As String, wrkbrACIHigh As String
            
            Branch.MoveFirst  ' there's exactly one row in this table that contains low and high ACI
            LowACI = Branch!brlowaci
            HighACI = Branch!brhighaci
        
        If PUBranchYN And Not PUCarrier And Not DelBranchYN And DelCarrier And _
            (PUACI >= LowACI And PUACI <= HighACI And DelACI >= LowACI And DelACI <= HighACI) Then
            ' Transfer = True
                FAns = 8
        ElseIf PUACI < LowACI Or PUACI > HighACI Or DelACI < LowACI Or DelACI > HighACI Then
            'HotShotOrder = True
            FAns = 4
        ' 2019-11-18: Anything that's picked up from a carrier is a recovery
        'ElseIf Not PUBranchYN And PUCarrier And Not DelBranchYN And Not DelCarrier Then
        ElseIf Not PUBranchYN And PUCarrier And Not DelCarrier Then
            'Recovery = true
            FAns = 1
        ElseIf Not PUBranchYN And Not PUCarrier And Not DelBranchYN And DelCarrier Then
            'Drop = True
            FAns = 2
        ElseIf Not PUBranchYN And PUCarrier And Not DelBranchYN And DelCarrier Then
            ' Drop = True  Carrier to Carrier priced like a drop
            FAns = 2
        ElseIf Not PUBranchYN And Not PUCarrier And Not DelBranchYN And Not DelCarrier Then
            'Point to Point = True
            FAns = 3
        ElseIf PUBranchYN And Not PUCarrier And DelBranchYN And Not DelCarrier Then
            'Dock Transfer = True
            FAns = 5
        ElseIf Not PUBranchYN And DelBranchYN And Not DelCarrier Then
    '    ElseIf Not PUBranchYN And Not PUCarrier And DelBranchYN And Not DelCarrier Then
            'Pickup = True
            FAns = 9
        ElseIf PUBranchYN And Not PUCarrier And Not DelBranchYN And Not DelCarrier Then
            'Delivery = True
            FAns = 10
        End If
           
        HTC200F_SetOrderType = FAns
        
    End Function
    
