

Private Sub btn_SaveChanges_Click()

    Dim db As Database: Set db = CurrentDb
    
    Dim Msg As String, MsgTitle As String
    Dim Ans As Integer
     
    MsgTitle = "Further Action Needed"
    Msg = ""
    
    Dim SavedCOid As Integer, SavedBrID As Integer, SavedOrderNo As Double
    Dim SavedHAWB As String
'Stop
    'If Not chk_AutosOK Then
    '        Msg = "Please get default assessorials and charges calculated and verified before creating this order"
    'ElseIf Not chk_CalcCompleted Then
    '    Msg = "Please calculate charges and verify result before creating this order"
    'End If

    If Forms![HTC200_G030_F120x Orders Vitals]!Curr_CustID = 0 Or _
        Forms![HTC200_G030_F120x Orders Vitals]!Curr_PUID = 0 Or _
        Forms![HTC200_G030_F120x Orders Vitals]!Curr_DelID = 0 Then
            Msg = "A minimum of customer, pickup, and delivery info are " & _
                "required to start an order." & vbCrLf & vbCrLf & _
                "The 'Save New Order' operation is cancelled."
    End If
    
    If Msg <> "" Then
        Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
        Exit Sub
    End If
    
    Dim wrkOrderType As Integer
    Dim OrderTypeName As String
    
    wrkOrderType = HTC200_SetOrderType(Me.new_PUACI, Me.new_chk_PUBranchAddressYN, Me.new_chk_PUCarrierYN, _
                                       Me.new_DelACI, Me.new_chk_DelBranchAddressYN, Me.new_chk_DelCarrierYN)
    
    Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo = NextOrderNo
    
' post order number to all sibling segments of the new order
    
    'Order Details
    Dim OO_Details As Recordset: Set OO_Details = db.OpenRecordset("HTC200_G030_T120 One Orders Details", dbOpenTable)
    With OO_Details
        If Not .EOF Then
            .MoveFirst
            Do Until .EOF
                .Edit
                    !M_OrderNo = Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo
                .Update
                .MoveNext
            Loop
        End If
    End With
    
    'Order Assessorials
    Dim OO_Assessorials As Recordset: Set OO_Assessorials = db.OpenRecordset("HTC200_G030_T120a One Orders Assessorials", dbOpenTable)
    With OO_Assessorials
        If Not .EOF Then
            .MoveFirst
            Do Until .EOF
                .Edit
                    !OA_OrderNo = Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo
                .Update
                .MoveNext
            Loop
        End If
    End With
    
    'Order Dims
    Dim OO_Dims As Recordset: Set OO_Dims = db.OpenRecordset("HTC200_G030_T120B One Orders Dims", dbOpenTable)
    With OO_Dims
        If Not .EOF Then
            .MoveFirst
            Do Until .EOF
                .Edit
                    !OD_OrderNo = Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo
                .Update
                .MoveNext
            Loop
        End If
    End With
    
    'Order Drivers
    Dim OO_Drivers As Recordset: Set OO_Drivers = db.OpenRecordset("HTC200_G030_T120C One Orders Drivers", dbOpenTable)
    With OO_Drivers
        If Not .EOF Then
            .MoveFirst
            Do Until .EOF
                .Edit
                    !odvr_orderno = Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo
                .Update
                .MoveNext
            Loop
        End If
    End With
    
    'Order Attachments
    Dim OO_Attachments As Recordset: Set OO_Attachments = db.OpenRecordset("HTC200_G030_T120D One Orders Attachments", dbOpenTable)
    With OO_Attachments
        If Not .EOF Then
            .MoveFirst
            Do Until .EOF
                .Edit
                    !OAtt_OrderNo = Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo
                .Update
                .MoveNext
            Loop
        End If
    End With
    
    Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderType = wrkOrderType
    
    OrderTypeName = HTC200_GetOrderTypeName(wrkOrderType)
'Stop
    lbl_OrderType.Caption = OrderTypeName
    Me.Recalc

    'Statseq 120 => "Delivered"
    If Me.new_StatSeq = 120 And _
        (Me.new_PODSig = "" Or Me.new_PODDate = "" Or Me.new_PODTime = "") Then
            DoCmd.OpenForm "HTC200_G030_F110_02 POD Update", , , , , acDialog
    End If
    
    'Dim db As Database
    'Set db = CurrentDb
    
    Dim OpenOrders As Boolean, InvcdOrders As Boolean, RemainingOrders As Boolean
    OpenOrders = False: InvcdOrders = False: RemainingOrders = False
    
    Dim DestTbl(5) As String
    Dim Stat As Integer
    Stat = Forms![HTC200_G030_F120x Orders Vitals]!curr_StatSeq
    
    'If Stat >= 30 And Stat < 190 Then     'Changed 2020-03-27
    If Stat < 190 Then
        DestTbl(1) = "HTC300_G040_T010A Open Orders"
        DestTbl(2) = "HTC300_G040_T011A Open Order Assessorials"
        DestTbl(3) = "HTC300_G040_T012A Open Order Dims"
        DestTbl(4) = "HTC300_G040_T013A Open Order Drivers"
        DestTbl(5) = "HTC300_G040_T014A Open Order Attachments"
    ElseIf Stat = 190 Then
        DestTbl(1) = "HTC300_G040_T010B Invoiced Orders"
        DestTbl(2) = "HTC300_G040_T011B Invoiced Assessorials"
        DestTbl(3) = "HTC300_G040_T012B Invoiced Dims"
        DestTbl(4) = "HTC300_G040_T013B Invoiced Drivers"
        DestTbl(5) = "HTC200_G040_T014B Invoiced Order Attachments"
    Else
        DestTbl(1) = "HTC300_G040_T010C Remaining Orders"
        DestTbl(2) = "HTC300_G040_T011C Remaining Order Assessorials"
        DestTbl(2) = "HTC300_G040_T011C Remaining Order Assessorials"
        DestTbl(3) = "HTC300_G040_T012C Remaining Order Dims"
        DestTbl(4) = "HTC300_G040_T013C Remaining Order Drivers"
        DestTbl(5) = "HTC300_G040_T014C Remaining Order Attachments"
    End If
    
    ' <<<  Destination Tables >>>>>>>>>
    Dim Orders As Recordset
    Set Orders = db.OpenRecordset(DestTbl(1), dbOpenDynaset)
    
    Dim Asses As Recordset
    Set Asses = db.OpenRecordset(DestTbl(2), dbOpenDynaset)
    
    Dim Dims As Recordset
    Set Dims = db.OpenRecordset(DestTbl(3), dbOpenDynaset)
    
    Dim Drivers As Recordset
    Set Drivers = db.OpenRecordset(DestTbl(4), dbOpenDynaset)
    
    Dim Attachments As Recordset
    Set Attachments = db.OpenRecordset(DestTbl(5), dbOpenDynaset)
    
    ' <<<<<<<<<<<<   Source Tables  >>>>>>>>>>>>>
    
    Dim NewDims As Recordset
    Set NewDims = db.OpenRecordset("HTC200_G030_T120B One Orders Dims", dbOpenTable)
    
    Dim NewAsses As Recordset
    Set NewAsses = db.OpenRecordset("HTC200_G030_T120A One Orders Assessorials", dbOpenTable)
    
    Dim NewDrivers As Recordset
    Set NewDrivers = db.OpenRecordset("HTC200_G030_T120C One Orders Drivers", dbOpenTable)
    
    Dim NewAttachments As Recordset
    Set NewAttachments = db.OpenRecordset("HTC200_G030_T120D One Orders Attachments", dbOpenTable)
    
    Dim ErrorLog As Recordset
    Set ErrorLog = db.OpenRecordset("HTC300_G000_T000 Error Log", dbOpenDynaset)
    
    '======== Save areas to accommodate "Create Same As" process ============
    
    Dim Svd_CoID As Integer, Svd_BrID As Integer, Svd_OrderNo As Double
    Dim Svd_OrderNotes As String
    Dim Svd_CusID As Integer, Svd_CustName As String, Svd_CusAssessorials As String
    Dim Svd_QBCusid As String, Svd_QBCusName As String, Svd_Tariff As String
    Dim Svd_CusAgentID As Integer, Svd_eMailReqd As Boolean
    
    Dim Svd_PUDate As String, Svd_PUTimeStart As String, Svd_PUTimeEnd As String
    Dim Svd_PUID As Integer, Svd_PUCo As String, Svd_PUACI As String
    Dim Svd_PUAddr1 As String, Svd_PUAddr2 As String, svd_PUCity As String
    Dim svd_PUState As String, Svd_PuCountry As String
    Dim Svd_PUZip As String, Svd_PUAssessorials As String
    Dim Svd_PUContactName As String, Svd_PUContactMeans As String, Svd_PUNotes As String
    Dim Svd_PUCarrierYN As Boolean, Svd_PUIntlYN As Boolean
    Dim Svd_PULocalYN As Boolean, Svd_PUBranchYN As Boolean
    
    Dim Svd_DelDate As String, Svd_DelTimeStart As String, Svd_DelTimeEnd As String
    Dim Svd_DelID As Integer, Svd_DelCo As String, Svd_Del_ACI As String
    Dim Svd_DelAddr1 As String, Svd_DelAddr2 As String, Svd_DelCity As String
    Dim Svd_DelState As String, Svd_DelCountry As String
    Dim Svd_DelZip As String, Svd_DelACI As String, Svd_DelAssessorials As String
    Dim Svd_DelContactName As String, Svd_DelContactMeans As String, Svd_DelNotes As String
    Dim Svd_DelCarrierYN As Boolean, Svd_DelIntlYN As Boolean
    Dim Svd_DelLocalYN As Boolean, Svd_DelBranchYN As Boolean
    
     '======== End Save areas to accommodate "Create Same As" process ========
       
AddOrder:

'Stop

    'Err.Number
  '*************************************************************
    On Error GoTo GetAnotherOrderNo
  '*************************************************************
    With Orders
        .AddNew
            !M_CoID = Forms![HTC200_G030_F120x Orders Vitals]!curr_CoID
            !M_BrID = Forms![HTC200_G030_F120x Orders Vitals]!curr_BrID
            !M_OrderNo = Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo
            SavedCOid = !M_CoID: Svd_CoID = SavedCOid
            SavedBrID = !M_BrID: Svd_BrID = SavedBrID
            SavedOrderNo = !M_OrderNo: Svd_OrderNo = SavedOrderNo
            SavedHAWB = Me.New_HAWB
            
            !M_OrderType = Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderType
            !M_CustomerID = Forms![HTC200_G030_F120x Orders Vitals]!Curr_CustID: Svd_CusID = !M_CustomerID
            !m_Customer = Me.New_Customer: Svd_CustName = !m_Customer
            If IsNull(new_AgentID) Then new_AgentID = 0
            !M_CustAgent = new_AgentID: Svd_CusAgentID = !M_CustAgent
            !M_Tariff = Forms![HTC200_G030_F120x Orders Vitals]!curr_Tariff: Svd_Tariff = !M_Tariff
            !M_CustAssessorials = new_CusAssessorials: Svd_CusAssessorials = !M_CustAssessorials
            !M_HAWB = New_HAWB
            !M_MAWB = new_MAWB
            '!M_Carrier = OO!M_Carrier
            !M_ProNbr = new_ProNbr
            
            !M_OrderNotes = new_OrderNotes: Svd_OrderNotes = !M_OrderNotes
                       
            !M_PUDate = new_PUDate: Svd_PUDate = !M_PUDate
            !M_PUTimeStart = new_PUTimeStart: Svd_PUTimeStart = !M_PUTimeStart
            !M_PUTimeEnd = new_PUTimeEnd: Svd_PUTimeEnd = !M_PUTimeEnd
            !M_DelDate = new_DelDate: Svd_DelDate = !M_DelDate
            !M_DelTimeStart = new_DelTimeStart: Svd_DelTimeStart = !M_DelTimeStart
            !M_DelTimeEnd = new_DelTimeEnd: Svd_DelTimeEnd = !M_DelTimeEnd
            !M_DeclaredValue = new_DeclaredValue
            !M_StorageChgs = new_StorageChgs
            !M_PUID = Forms![HTC200_G030_F120x Orders Vitals]!Curr_PUID: Svd_PUID = !M_PUID
            !M_PUCo = new_PUCo: Svd_PUCo = !M_PUCo
            !M_PULocn = new_PUAddr1 & ", " & IIf(Len(new_PUAddr2) > 0, new_PUAddr2 & ", ", "") & _
                        new_PUCity & ", " & new_PUState & ", " & new_PUCountry
            Svd_PUAddr1 = Me.new_PUAddr1: Svd_PUAddr2 = Me.new_PUAddr2
            svd_PUCity = Me.new_PUCity: svd_PUState = Me.new_PUState: Svd_PuCountry = Me.new_PUCountry
            !M_PUZip = new_PUZip: Svd_PUZip = !M_PUZip
            !M_PULatitude = "": !M_PULongitude = ""
            If Len(new_PUACI) > 1 Then new_PUACI = Left(Trim(new_PUACI), 1)
            !M_PUACI = new_PUACI: Svd_PUACI = !M_PUACI
            !M_PUAssessorials = new_PUAssessorials: Svd_PUAssessorials = !M_PUAssessorials
            !M_PUContactName = new_PUContact: Svd_PUContactName = !M_PUContactName
            !M_PUContactMeans = new_PUContactMeans: Svd_PUContactMeans = !M_PUContactMeans
            !M_PUNotes = new_PUNotes: Svd_PUNotes = !M_PUNotes
            !M_PUCarrierYN = Me.new_chk_PUCarrierYN: Svd_PUCarrierYN = !M_PUCarrierYN
            !M_PUIntlYN = Me.new_chk_PUIntlYN: Svd_PUIntlYN = !M_PUIntlYN
            !M_PULocalYN = Me.new_chk_PULocalYN: Svd_PULocalYN = !M_PULocalYN
            !M_PUBranchYN = Me.new_chk_PUBranchAddressYN: Svd_PUBranchYN = !M_PUBranchYN
            !M_DelID = Forms![HTC200_G030_F120x Orders Vitals]!Curr_DelID: Svd_DelID = !M_DelID
            !M_DelCo = new_DelCo: Svd_DelCo = !M_DelCo
            !M_DelLocn = new_DelAddr1 & ", " & IIf(Len(new_DelAddr2) > 0, new_DelAddr2 & ", ", "") & _
                        new_DelCity & ", " & new_delState & ", " & new_DelCountry
            Svd_DelAddr1 = Me.new_DelAddr1: Svd_DelAddr2 = Me.new_DelAddr2
            Svd_DelCity = Me.new_DelCity: Svd_DelState = Me.new_delState: Svd_DelCountry = Me.new_DelCountry
            !M_DelZip = new_DelZip: Svd_DelZip = !M_DelZip
            !M_DelLatitude = "": !M_DelLongitude = ""
            If Len(new_DelACI) > 1 Then new_DelACI = Left(Trim(new_DelACI), 1)
            !M_DelACI = new_DelACI: Svd_DelACI = !M_DelACI
            !M_Del_Assessorials = new_DelAssessorials: Svd_DelAssessorials = !M_Del_Assessorials
            !M_DelContactName = new_DelContact: Svd_DelContactName = !M_DelContactName
            !M_DelContactMeans = new_DelcontactMeans: Svd_DelContactMeans = !M_DelContactMeans
            !M_DelNotes = new_DelNotes: Svd_DelNotes = !M_DelNotes
            !M_DelCarrierYN = Me.new_chk_DelCarrierYN: Svd_DelCarrierYN = !M_DelCarrierYN
            !M_DelIntlYN = Me.new_chk_DelIntlYN: Svd_DelIntlYN = !M_DelIntlYN
            !M_DelLocalYN = Me.new_chk_DelLocalYN: Svd_DelLocalYN = !M_DelLocalYN
            !M_DelBranchYN = Me.new_chk_DelBranchAddressYN: Svd_DelBranchYN = !M_DelBranchYN
            !M_PODSig = new_PODSig
            
            If IsDate(new_PODDate) Then
                !M_PODDate = new_PODDate
                !M_PODTime = new_PODTime
            Else
                !M_PODDate = ""
                !M_PODTime = ""
            End If
            
            !M_PODNotes = new_PODNotes
            !M_Status = new_Status
            !m_StatSeq = Forms![HTC200_G030_F120x Orders Vitals]!curr_StatSeq
            !M_Rate = new_WeightChgs
            !M_FSC = new_FSCChgs
            !M_Services = new_AssessorialChgs
            !M_StorageChgs = new_StorageChgs
            !M_Adjustments = new_AdjustmentChgs
            !M_RatingNotes = Me.new_RatingNote
            !M_Charges = new_WeightChgs + new_FSCChgs + new_AssessorialChgs + new_AdjustmentChgs + new_StorageChgs
            !M_Costs = new_Expenses
            !M_QBCustomerListID = Me.QBCustID
            !M_QBCustFullName = Me.QBCustName
            !M_AutoAssessYN = Me.chk_AutosOK
            !M_WgtChgsCalcYN = Me.chk_CalcCompleted
        .Update
        .Close
        GoTo OrderAdded
    End With
  '*************************************************************
  '  On Error 3022 GoTo GetAnotherOrderNo
  '*************************************************************
GetAnotherOrderNo:
'Stop
    If Err.Number = 3022 Then
        Msg = "Order Number " & Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo & " already exists. "
        Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo = NextOrderNo()
        Forms![HTC200_G030_F130 New Order].Requery
        Msg = Msg & "The order number has been changed to " & Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo
        Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
    Else
        Msg = "Error # " & Err.Number & " occurred when adding an order number, " & vbCrLf & _
            "Order " & Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo & " not added, " & vbCrLf & _
            "HTC200_G030_F030 New Order aborted."
        Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
        ErrorLog.AddNew
            ErrorLog!ErrWhen = Now()
            ErrorLog!ErrrLid = Forms![HTC200_G000_F000 Main Menu]!hdn_LID
            ErrorLog!ErrPCLid = Forms![HTC200_G000_F000 Main Menu]!hdn_PCLID
            ErrorLog!ErrObjectName = "HTC200_G030_F130 New Order"
            ErrorLog!ErrModuleName = "btn_SaveChanges_Click()"
            ErrorLog!ErrDescription = Msg
        ErrorLog.Update
        Err.Clear
        On Error GoTo 0    ' <== this command may be redundant as err.clear may have made the reset already
        Call HTC200_RemoveOIW(SavedCOid, SavedBrID, SavedOrderNo)     'Remove order number from the Orders in Work table
        DoCmd.Close
    End If
    GoTo AddOrder
    
    
OrderAdded:
    Call HTC200_PosttoLON(SavedCOid, SavedBrID, SavedOrderNo)     ' post the order number just added to the last order number ordered table
    Call HTC200_RemoveOIW(SavedCOid, SavedBrID, SavedOrderNo)     'Remove order number from the Orders in Work table
                
    If Me.new_chk_PULocalYN <> Me.chk_OrigPUL Or _
       Me.new_chk_PUCarrierYN <> Me.chk_OrigPUC Or _
       Me.new_chk_PUIntlYN <> Me.chk_OrigPUi Then
            MsgTitle = "Save Changes"
            Msg = "Do you want to save changes made to Pickup Location's Local, Carrier, and/or Intl settings?"
            Ans = MsgBox(Msg, vbYesNo, MsgTitle)
            If Ans = vbYes Then
                Call HTC200_UpdateAddressSwitches(Forms![HTC200_G030_F120x Orders Vitals]!curr_CoID, _
                                                  Forms![HTC200_G030_F120x Orders Vitals]!curr_BrID, _
                                                  Forms![HTC200_G030_F120x Orders Vitals]!Curr_PUID, _
                                                  Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo, _
                                                  Me.new_chk_PULocalYN, Me.new_chk_PUCarrierYN, Me.new_chk_PUIntlYN, _
                                                  Me.chk_PULclUpdt, Me.chk_PuCarUpdt, Me.chk_PUIntlUpdt)
            End If
    End If
    
    If Me.new_chk_DelLocalYN <> Me.chk_OrigDelL Or _
       Me.new_chk_DelCarrierYN <> Me.chk_OrigDelC Or _
       Me.new_chk_DelIntlYN <> Me.chk_OrigDeli Then
            MsgTitle = "Save Changes"
            Msg = "Do you want to save changes made to Delivery Location's Local, Carrier, and/or Intl settings?"
            Ans = MsgBox(Msg, vbYesNo, MsgTitle)
            If Ans = vbYes Then
                Call HTC200_UpdateAddressSwitches(Forms![HTC200_G030_F120x Orders Vitals]!curr_CoID, _
                                                  Forms![HTC200_G030_F120x Orders Vitals]!curr_BrID, _
                                                  Forms![HTC200_G030_F120x Orders Vitals]!Curr_DelID, _
                                                  Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo, _
                                                  Me.new_chk_DelLocalYN, Me.new_chk_DelCarrierYN, Me.new_chk_DelIntlYN, _
                                                  Me.chk_DelLclUpdt, Me.chk_DelCarUpdt, Me.chk_DelIntlUpdt)
            End If
    End If
    
    Dim DimsCnt As Integer: DimsCnt = 0
    Dim AssesCnt As Integer: AssesCnt = 0
    Dim DriverCnt As Integer: DriverCnt = 0
    Dim AttachmentsCnt As Integer: AttachmentsCnt = 0
    
    Dim x As Integer
    
    If Not NewAsses.EOF Then
        With NewAsses
            .MoveFirst
            Do Until .EOF
                Asses.AddNew
                    Asses!OA_COID = Forms![HTC200_G030_F120x Orders Vitals]!curr_CoID
                    Asses!OA_BrID = Forms![HTC200_G030_F120x Orders Vitals]!curr_BrID
                    Asses!OA_OrderNo = Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo
                    Asses!OA_AssNo = !OA_AssNo
                    Asses!OA_AssParent = !OA_AssParent
                    Asses!OA_AssID = !OA_AssID
                    Asses!OA_ShipperFee = !OA_ShipperFee
                    Asses!OA_MinutesWaitTime = !OA_MinutesWaitTime
                    Asses!OA_AWBValue = !OA_AWBValue
                    Asses!OA_HowMuch = !OA_HowMuch
                    Asses!OA_HowManyMiles = !OA_HowManyMiles
                    Asses!OA_TotalCharges = !OA_TotalCharges
                    Asses!OA_HowMuchPerPound = !OA_HowMuchPerPound
                    Asses!OA_HowManyHrs = !OA_HowManyHrs
                    Asses!OA_Presentation = !OA_Presentation
                Asses.Update
                AssesCnt = AssesCnt + 1
                .MoveNext
            Loop
            .Close
            Asses.Close
        End With
    End If
    
    If Not NewDims.EOF Then
        NewDims.MoveFirst
        NewDims.MoveLast
        If NewDims.RecordCount > 0 Then
            DimsCnt = NewDims.RecordCount
            With NewDims
                .MoveFirst
                Do Until .EOF
                    Dims.AddNew
                        Dims!OD_CoID = Forms![HTC200_G030_F120x Orders Vitals]!curr_CoID
                        Dims!OD_BrID = Forms![HTC200_G030_F120x Orders Vitals]!curr_BrID
                        Dims!OD_OrderNo = Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo
                        Dims!OD_DimID = !OD_DimID
                        Dims!OD_UnitType = !OD_UnitType
                        Dims!OD_UnitQty = !OD_UnitQty
                        Dims!OD_UnitHeight = !OD_UnitHeight
                        Dims!OD_UnitLength = !OD_UnitLength
                        Dims!OD_UnitWidth = !OD_UnitWidth
                        Dims!OD_UnitWeight = !OD_UnitWeight
                        Dims!OD_UnitDimWeight = !OD_UnitDimWeight
                    Dims.Update
                    .MoveNext
                Loop
                .Close
                Dims.Close
            End With
        End If
    End If
    
    If Not NewDrivers.EOF Then
        NewDrivers.MoveFirst
        NewDrivers.MoveLast
            If NewDrivers.RecordCount > 0 Then
                DriverCnt = NewDrivers.RecordCount
                With NewDrivers
                    .MoveFirst
                    Do Until .EOF
                        Drivers.AddNew
                            Drivers!odvr_coid = Forms![HTC200_G030_F120x Orders Vitals]!curr_CoID
                            Drivers!odvr_brid = Forms![HTC200_G030_F120x Orders Vitals]!curr_BrID
                            Drivers!odvr_orderno = Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo
                            Drivers!odvr_dvrno = !odvr_dvrno
                            Drivers!odvr_empid = !odvr_empid
                            Drivers!odvr_name = !odvr_name
                        Drivers.Update
                        .MoveNext
                    Loop
                    .Close
                    Drivers.Close
                End With
            End If
    End If
    
    Dim HTCAttach As String: HTCAttach = ""
    Dim AttachSource As String: AttachSource = ""
        
    'AttachSource is obtained from the branch info and is the path containing
    '      the file to be moved from there to the folder group defined in HTCAttach
    
    'HTCAttach is obtained from the branch info and is the path to the location
    '      under which all attachments assigned to an order are placed
    
    Dim Branches As Recordset
    Set Branches = db.OpenRecordset("HTC300_G000_T020 Branch Info", dbOpenDynaset)
    
    With Branches
        If Not .EOF Then
            .MoveFirst
            Do Until .EOF
                If !BrCoID = Forms![HTC200_G030_F120x Orders Vitals]!curr_CoID And _
                    !BrID = Forms![HTC200_G030_F120x Orders Vitals]!curr_BrID Then
                        AttachSource = !brscantolocn
                        HTCAttach = !brdocstoragelocn
                        Exit Do
                End If
                .MoveNext
            Loop
            If .EOF Then
                MsgTitle = "HTC200_G030_F130 New Order, Btn: Save Order"
                Msg = "Can't find Co-Br '" & Forms![HTC200_G030_F120x Orders Vitals]!curr_CoID & _
                        "-" & Forms![HTC200_G030_F120x Orders Vitals]!curr_BrID
                Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
            End If
        Else
            MsgTitle = "HTC200_G030_F130 New Order, Btn: Save Order"
            Msg = "The are no branches defined"
            Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
        End If
    End With
                
    If HTCAttach = "" Then
        GoTo SkipAttachments
    Else
        Dim wFileAndPath As String 'this is the complete path to where the scanner put the doc
        Dim wFile As String
        Dim i As Integer, f As Integer
        
        Dim ReturnLocn As String 'The full path to the attachment assigned to the new ordeeeee
        
        If Not NewAttachments.EOF Then
            NewAttachments.MoveFirst
            NewAttachments.MoveLast
            If NewAttachments.RecordCount > 0 Then
                AttachmentsCnt = NewAttachments.RecordCount
                With NewAttachments
                    .MoveFirst
                    Do Until .EOF
                        Attachments.AddNew
                            Attachments!att_COID = Forms![HTC200_G030_F120x Orders Vitals]!curr_CoID
                            Attachments!att_BrID = Forms![HTC200_G030_F120x Orders Vitals]!curr_BrID
                            Attachments!att_OrderNo = Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo
                            Attachments!att_CustID = Forms![HTC200_G030_F120x Orders Vitals]!Curr_CustID
    
                            ' pick filename out of the path
                            wFileAndPath = !oatt_path
                            wFile = ""
                            
                            f = 0
                            For i = Len(wFileAndPath) To 1 Step -1
                                If Mid(wFileAndPath, i, 1) = "\" Then Exit For
                                f = f + 1
                            Next i
                            wFile = Right(wFileAndPath, f)
                            
                            Call HTC200_StoreAttachment(AttachSource, HTCAttach, _
                                                    Forms![HTC200_G030_F120x Orders Vitals]!curr_CoID, _
                                                    Forms![HTC200_G030_F120x Orders Vitals]!curr_BrID, _
                                                    Forms![HTC200_G030_F120x Orders Vitals]!Curr_CustID, _
                                                    Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo, _
                                                    wFile, ReturnLocn)
                            
                            Attachments!att_path = ReturnLocn
                        Attachments.Update
                        .MoveNext
                    Loop
                End With
            End If
        End If
    End If
    
SkipAttachments:

    'Try to save the customer/hawb value.
    'In certain cases, reusing the Customer/HAWB value is OK, hence the 'on error' action
    

    If Len(Trim(SavedHAWB)) > 0 Then
       Dim UsedHAWBs As Recordset
       Set UsedHAWBs = db.OpenRecordset("HTC300_G040_T040 HAWB Values", dbOpenDynaset)
       
       On Error Resume Next
            With UsedHAWBs
                 .AddNew
                     !existinghawbvalues = SavedHAWB
                     !hawbcoid = SavedCOid
                     !hawbbrid = SavedBrID
                     !hawbcustomerid = Forms![HTC200_G030_F120x Orders Vitals]!Curr_CustID
                     !hawborder = SavedOrderNo
                 .Update
                .Close
             End With
        On Error GoTo 0
    End If
    
    Dim eMMsgTitle As String
    Dim eMMsgBody As String
    
    Dim Hist As Recordset
    Set Hist = db.OpenRecordset("HTC300_G040_T030 Orders Update History", dbOpenDynaset)
    
    ' --------------- don't forget history ------------
    
    With Hist
        .AddNew
            !Orders_UpdtDate = Now()
            !Orders_UpdtLID = fOSUserName()
            !Orders_CoID = Forms![HTC200_G030_F120x Orders Vitals]!curr_CoID
            !Orders_BrID = Forms![HTC200_G030_F120x Orders Vitals]!curr_BrID
            !Orders_OrderNbr = Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo
            !Orders_Changes = "Order #" & Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo & _
                                " from " & HTC200_GetCusName(Forms![HTC200_G030_F120x Orders Vitals]!curr_CoID, _
                                                             Forms![HTC200_G030_F120x Orders Vitals]!curr_BrID, _
                                                             Forms![HTC200_G030_F120x Orders Vitals]!Curr_CustID) & " (#" & _
                                          Forms![HTC200_G030_F120x Orders Vitals]!Curr_CustID & ") Created with " & _
                                          DimsCnt & " Dims, " & AssesCnt & " Assessorials, and " & DriverCnt & " Drivers; " & _
                                          AttachmentsCnt & " Attachments; " & _
                                          FormatCurrency(new_WeightChgs + new_FSCChgs + new_AssessorialChgs + new_AdjustmentChgs + new_StorageChgs) & _
                                          IIf(Me.new_AdjustmentChgs <> 0, " Rating Notes: " & Me.new_RatingNote & "; ", "") & _
                                          " Total Charges using the " & Forms![HTC200_G030_F120x Orders Vitals]!curr_Tariff & " tariff; " & _
                                          "Status = '" & new_Status & " (" & Forms![HTC200_G030_F120x Orders Vitals]!curr_StatSeq & "')" & _
                                          IIf(Me.txt_SpclPUMsg <> "", ", " & Me.txt_SpclPUMsg, "") & _
                                          IIf(Me.txt_SpclDelMsg <> "", ", " & Me.txt_SpclDelMsg, "") & _
                                          IIf(Me.chk_eMailReqd And Me.new_AgentID > 0, "eMail sent to Agent", "") & _
                                          IIf(Me.chk_eMailReqd And Me.new_AgentID = 0, "No agent listed, no eMail sent", "") & _
                                          IIf(Not Me.chk_eMailReqd And Me.new_AgentID > 0, " no eMail sent", "")
            If Me.chk_eMailReqd And Me.new_AgentID > 0 Then
                eMMsgTitle = "Order #" & Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo & " Created" & vbCrLf & " " & vbCrLf
                eMMsgBody = "Order " & !Orders_OrderNbr & " created for:" & vbCrLf & "   " & vbCrLf & _
                            Me.New_Customer & vbCrLf & "   " & _
                            "House Bill: " & Me.New_HAWB & vbCrLf & "   " & _
                            "Pickup: " & Me.new_PUCo & vbCrLf & "   " & _
                            "Deliver To: " & Me.new_DelCo & vbCrLf & "   " & _
                            "Status: " & Me.new_Status
                If Me.new_PODSig <> "" Then
                    eMMsgBody = eMMsgBody & vbCrLf & vbCrLf & _
                                "POD Signed By: " & Me.new_PODSig & " on " & Me.new_PODDate & " at " & Me.new_PODTime
                End If
                Call HTC200_SendEmail(!Orders_CoID, !Orders_BrID, !Orders_OrderNbr, Me.new_AgentID, _
                                        eMMsgTitle, eMMsgBody, True)
                !Orders_Changes = !Orders_Changes & vbCrLf & " " & vbCrLf & eMMsgBody
            End If
        .Update
        .Close
    End With
    
    'Dim PrintRequested As Boolean: PrintRequested = False
    'Dim AddAnotherOrder As Boolean: AddAnotherOrder = False

    MsgTitle = "Confirmation"
    Msg = "Order " & Forms![HTC200_G030_F120x Orders Vitals]!curr_OrderNo & " created"
    Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
    
    Dim SameAs As Recordset
    Set SameAs = db.OpenRecordset("HTC200_G030_T130 CreateSameAsInfo", dbOpenTable)
    
    ' =====================================================================
    'Option to print order after creation is nix'd in version xx, 2021-06-18
    ' and [HTC200_G030_F130b New Order Whats Next] was created to indicate
    ' desire to
    '   (1) create another new order starting from scratch,
    'or (2) Begin a new order with the next order number and same Customer, Agent,
    '       pick up date/time, (4) delivery date/time, (5) a default DIM and set
    '       focus on HAWB
    'or (3) exit the new order process.
        
    'Note the request to print he order just added can be satisfied only
    '     if the order was created in the open orders table
    
    'If Stat >= 30 And Stat < 190 Then
    '    MsgTitle = "Print It?"
    ''    Msg = "Print the order just added?"
    '    Ans = MsgBox(Msg, vbYesNo, MsgTitle)
    '    If Ans = vbYes Then PrintRequested = True
    'End If
    
    'If PrintRequested And Stat >= 30 And Stat < 190 Then
    '     Call HTC200_PrintOrder(SavedCOid, SavedBrID, SavedOrderNo)
    'End If
    
    'MsgTitle = "Question"
    'Msg = "Add Another New Order?"
    'Ans = MsgBox(Msg, vbYesNo, MsgTitle)
    'If Ans = vbYes Then AddAnotherOrder = True
    ' =====================================================================

    DoCmd.OpenForm "HTC200_G030_F130b New Order Whats Next", , , , , acDialog

    If Me.WhatsNext = 1 Then
        
        'Start a new order from scratch
        
        With SameAs
            If Not .EOF Then
                .MoveFirst
                Do Until .EOF
                    .Delete
                    .MoveNext
                Loop
            End If
        End With
        
        Call HTC200_MainBtnsSwitch("On")
        DoCmd.Close acForm, "HTC200_G030_F130 New Order"
        DoCmd.Close acForm, "HTC200_G030_F120x Orders Vitals"
        DoCmd.OpenForm "HTC200_G030_F100 Orders Selection"
        Forms![HTC200_G030_F100 orders Selection]![btn_New Order].SetFocus
        Forms![HTC200_G030_F100 orders Selection]![btn_New Order].SetFocus
        SendKeys "{ENTER}"
        
    ElseIf Me.WhatsNext = 3 Then
    
        ' exit new order process altogether
        
        With SameAs
            If Not .EOF Then
                .MoveFirst
                Do Until .EOF
                    .Delete
                    .MoveNext
                Loop
            End If
        End With
        
        Call HTC200_MainBtnsSwitch("On")
        DoCmd.Close acForm, "HTC200_G030_F130 New Order"
        DoCmd.Close acForm, "HTC200_G030_F120x Orders Vitals"
    
    ElseIf Me.WhatsNext = 2 Then
        
        'create a "Same As" info for next new order
        
        With SameAs
            If .EOF Then
'Stop
                .AddNew
                    !csa_coid = Svd_CoID: !csa_brid = Svd_BrID: !csa_orderno = Svd_OrderNo
                    !csa_ordernotes = Svd_OrderNotes
                    !csa_custid = Svd_CusID: !csa_custname = Svd_CustName
                    !csa_qbcusid = Svd_QBCusid: !csa_qbcusname = Svd_QBCusName
                    !csa_cusassessorials = Svd_CusAssessorials
                    !csa_cusagentid = Svd_CusAgentID: !csa_emailreqd = Svd_eMailReqd
                    !csa_tariff = Svd_Tariff
                    
                    !csa_pudate = Svd_PUDate: !csa_putimestart = Svd_PUTimeStart: !csa_putimeend = Svd_PUTimeEnd
                    !csa_puid = Svd_PUID: !csa_puco = Svd_PUCo
                    !csa_puaddrln1 = Svd_PUAddr1: !csa_puaddrln2 = Svd_PUAddr2: !csa_pucity = svd_PUCity
                    !csa_pustate = svd_PUState: !csa_pucountry = Svd_PuCountry
                    !csa_puzip = Svd_PUZip
                    !csa_puaci = Svd_PUACI: !csa_puassessorials = Svd_PUAssessorials
                    !csa_pucontactname = Svd_PUContactName: !csa_pucontactmeans = Svd_PUContactMeans
                    !csa_punotes = Svd_PUNotes
                    !csa_pucarrieryn = Svd_PUCarrierYN: !csa_puintlyn = Svd_PUIntlYN
                    !csa_pulocalyn = Svd_PULocalYN: !csa_pubranchyn = Svd_PUBranchYN
                    
                    !csa_Deldate = Svd_DelDate: !csa_Deltimestart = Svd_DelTimeStart: !csa_Deltimeend = Svd_DelTimeEnd
                    !csa_Delid = Svd_DelID: !csa_Delco = Svd_DelCo
                    !csa_Deladdrln1 = Svd_DelAddr1: !csa_Deladdrln2 = Svd_DelAddr2: !csa_Delcity = Svd_DelCity
                    !csa_Delstate = Svd_DelState: !csa_delcountry = Svd_DelCountry
                    !csa_Delzip = Svd_DelZip
                    !csa_delaci = Svd_DelACI: !csa_Delassessorials = Svd_DelAssessorials
                    !csa_Delcontactname = Svd_DelContactName: !csa_delcontactmeans = Svd_DelContactMeans
                    !csa_Delnotes = Svd_DelNotes
                    !csa_Delcarrieryn = Svd_DelCarrierYN: !csa_Delintlyn = Svd_DelIntlYN
                    !csa_Dellocalyn = Svd_DelLocalYN: !csa_Delbranchyn = Svd_DelBranchYN
                .Update
            End If
        End With
        Call HTC200_MainBtnsSwitch("On")
        DoCmd.Close acForm, "HTC200_G030_F130 New Order"
        DoCmd.Close acForm, "HTC200_G030_F120x Orders Vitals"
        DoCmd.OpenForm "HTC200_G030_F100 Orders Selection"
        Forms![HTC200_G030_F100 orders Selection]![btn_New Order].SetFocus
        Forms![HTC200_G030_F100 orders Selection]![btn_New Order].SetFocus
        SendKeys "{ENTER}"
    End If
 
End Sub